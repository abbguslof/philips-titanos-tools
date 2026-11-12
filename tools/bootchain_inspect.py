#!/usr/bin/env python3
"""Inspect local boot-chain dumps without touching the TV.

Reads the files produced by `tools/bootchain_dump.py`, parses U-Boot legacy
uImage headers, verifies header/data CRCs, reports entropy, and finds embedded
uImage headers and known strings. It never opens the TV or a block device.

Examples:
  python3 tools/bootchain_inspect.py --dir dist/bootchain/20260101T000000Z
  python3 tools/bootchain_inspect.py --dir dist/bootchain/20260101T000000Z --json

A data CRC mismatch on an encrypted/signed image is expected: the header may
carry the plaintext CRC while the partition holds the protected image. Do not
publish the raw dumps; this tool prints summaries only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

UIMAGE_MAGIC = b"\x27\x05\x19\x56"
UIMAGE_HEADER = 64
MARKERS = [
    b"U-Boot 2016.07",
    b"ATF",
    b"UMFG",
    b"NFSB",
    b"DBFG",
    b"ARMd",
    b"secos",
    b"Linux version",
]
OS_NAMES = {5: "Linux"}
ARCH_NAMES = {22: "arm64"}
TYPE_NAMES = {2: "kernel", 5: "filesystem", 7: "standalone", 8: "firmware"}
COMP_NAMES = {0: "none", 1: "gzip", 2: "bzip2", 3: "lzma", 4: "lzo", 5: "lz4"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def parse_uimage(data: bytes) -> dict | None:
    if len(data) < UIMAGE_HEADER or data[:4] != UIMAGE_MAGIC:
        return None
    (magic, hcrc, timestamp, size, load, entry, dcrc, os_id, arch, image_type, comp) = (
        struct.unpack(">7I4B", data[:32])
    )
    name = data[32:64].split(b"\0")[0].decode("latin1", "replace")
    header = bytearray(data[:UIMAGE_HEADER])
    header[4:8] = b"\0\0\0\0"
    header_ok = (zlib.crc32(bytes(header)) & 0xFFFFFFFF) == hcrc
    payload = data[UIMAGE_HEADER : UIMAGE_HEADER + size]
    data_ok = len(payload) == size and (zlib.crc32(payload) & 0xFFFFFFFF) == dcrc
    sample = payload[: 256 * 1024]
    found = []
    if len(payload) >= 0x40 and payload[0x38:0x3C] == b"ARM\x64":
        found.append("arm64-Image")
    if payload[:4] == b"\xd0\x0d\xfe\xed":
        found.append("fdt")
    return {
        "magic": f"0x{magic:08x}",
        "name": name,
        "timestamp": timestamp,
        "data_size": size,
        "load_address": f"0x{load:08x}",
        "entry_point": f"0x{entry:08x}",
        "os": OS_NAMES.get(os_id, str(os_id)),
        "arch": ARCH_NAMES.get(arch, str(arch)),
        "type": TYPE_NAMES.get(image_type, str(image_type)),
        "compression": COMP_NAMES.get(comp, str(comp)),
        "header_crc_ok": header_ok,
        "data_crc_ok": data_ok,
        "data_first_16": payload[:16].hex(),
        "payload_entropy_sample": round(entropy(sample), 3),
        "payload_magic": found,
        "complete": len(payload) == size,
    }


def find_uimages(data: bytes, limit: int = 20) -> list[dict]:
    found = []
    start = 0
    while len(found) < limit:
        offset = data.find(UIMAGE_MAGIC, start)
        if offset < 0:
            break
        parsed = parse_uimage(data[offset:])
        if parsed and parsed["header_crc_ok"]:
            parsed["offset"] = offset
            found.append(parsed)
            start = offset + UIMAGE_HEADER + parsed["data_size"]
        else:
            start = offset + 4
    return found


def marker_offsets(data: bytes) -> dict[str, list[int]]:
    out = {}
    for marker in MARKERS:
        positions = []
        start = 0
        while len(positions) < 5:
            pos = data.find(marker, start)
            if pos < 0:
                break
            positions.append(pos)
            start = pos + 1
        if positions:
            out[marker.decode("ascii", "replace")] = positions
    return out


def inspect_file(path: Path) -> dict:
    data = path.read_bytes()
    parsed = parse_uimage(data)
    record = {
        "file": path.name,
        "bytes": len(data),
        "sha256": sha256_file(path),
        "entropy_sample": round(entropy(data[: 1024 * 1024]), 3),
    }
    if parsed:
        record["uimage"] = parsed
    else:
        record["uimage"] = None
        record["embedded_uimages"] = find_uimages(data)
        record["markers"] = marker_offsets(data)
    return record


def format_record(record: dict) -> str:
    lines = [
        f"{record['file']}  {record['bytes']} bytes  sha256={record['sha256'][:16]}  entropy={record['entropy_sample']}"
    ]
    image = record.get("uimage")
    if image:
        lines.append(
            "  uImage"
            f" name={image['name']!r} type={image['type']} os={image['os']} arch={image['arch']}"
            f" data={image['data_size']} load={image['load_address']} entry={image['entry_point']}"
            f" comp={image['compression']}"
        )
        lines.append(
            f"  header_crc={'OK' if image['header_crc_ok'] else 'BAD'}"
            f" data_crc={'OK' if image['data_crc_ok'] else 'BAD'}"
            f" complete={image['complete']}"
            f" payload_magic={','.join(image['payload_magic']) or '-'}"
            f" first16={image['data_first_16']}"
            f" payload_entropy={image['payload_entropy_sample']}"
        )
    else:
        for embedded in record.get("embedded_uimages", []):
            lines.append(
                f"  embedded uImage at 0x{embedded['offset']:x}"
                f" name={embedded['name']!r} data={embedded['data_size']}"
                f" load={embedded['load_address']} entry={embedded['entry_point']}"
                f" data_crc={'OK' if embedded['data_crc_ok'] else 'BAD'}"
            )
        markers = record.get("markers") or {}
        if markers:
            lines.append(
                "  markers="
                + ", ".join(
                    f"{name}@" + ",".join(f"0x{pos:x}" for pos in positions)
                    for name, positions in markers.items()
                )
            )
    return "\n".join(lines)


def latest_dir(root: Path) -> Path:
    dirs = [path for path in root.iterdir() if path.is_dir()]
    if not dirs:
        raise SystemExit(f"no dump directories under {root}")
    return max(dirs, key=lambda path: path.name)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="", help="dump directory (default: latest under dist/bootchain)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.dir) if args.dir else latest_dir(Path("dist") / "bootchain")
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    files = sorted(root.glob("*.bin"))
    if not files:
        print(f"no .bin files under {root}", file=sys.stderr)
        return 2
    records = [inspect_file(path) for path in files]
    if args.json:
        print(json.dumps({"dir": root.name, "files": records}, indent=2, sort_keys=True))
    else:
        for record in records:
            print(format_record(record))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
