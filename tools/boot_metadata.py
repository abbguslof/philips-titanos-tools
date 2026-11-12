#!/usr/bin/env python3
"""Inspect the local p9 and vendor-boot metadata structures.

Reads the files from `tools/bootchain_dump.py` and prints the plaintext
structures: `DBFG`, `PPCH`, `FWVR`, `NVHC`, `UPST`, `STBC`, `UMFG` and `VTBL`.
The `PPCH` entry format is decoded; `NVHC` is summarized because its per-entry
layout is not fully mapped yet.

Local only. It never opens the TV, a block device, or the network. Raw dumps may
contain device identifiers; keep them out of git.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

MAGICS = [b"DBFG", b"PPCH", b"FWVR", b"NVHC", b"UPST", b"STBC", b"VTBL", b"UMFG", b"NFSB"]
PPCH_ENTRY = 60


def scan_magics(data: bytes) -> list[tuple[str, int]]:
    found = []
    for magic in MAGICS:
        start = 0
        while True:
            pos = data.find(magic, start)
            if pos < 0:
                break
            found.append((magic.decode("ascii"), pos))
            start = pos + 1
    return sorted(found, key=lambda item: item[1])


def parse_ppch(data: bytes, offset: int) -> dict | None:
    if data[offset : offset + 4] != b"PPCH":
        return None
    entries = []
    pos = offset + 8
    while pos + PPCH_ENTRY <= len(data):
        raw_name = data[pos : pos + 16]
        name = raw_name.split(b"\0")[0]
        if not name or any(byte < 32 or byte > 126 for byte in name):
            break
        raw_device = data[pos + 16 : pos + 48]
        device = raw_device.split(b"\0")[0].decode("latin1")
        entry_offset, flag, slot = struct.unpack("<III", data[pos + 48 : pos + 60])
        entries.append(
            {
                "name": name.decode("ascii"),
                "device": device,
                "offset": entry_offset,
                "flag": flag,
                "slot": slot,
            }
        )
        pos += PPCH_ENTRY
    return {"offset": offset, "crc": data[offset + 4 : offset + 8].hex(), "entries": entries, "end": pos}


def parse_stbc(data: bytes, offset: int) -> dict | None:
    if data[offset : offset + 4] != b"STBC":
        return None
    header = struct.unpack("<12I", data[offset : offset + 48])
    umfg = data.find(b"UMFG", offset, offset + 0x400)
    slot = None
    if umfg >= 0 and umfg + 8 <= len(data):
        slot = struct.unpack("<I", data[umfg + 4 : umfg + 8])[0]
    return {
        "offset": offset,
        "header": list(header),
        "umfg_offset": umfg,
        "slot": slot,
    }


def parse_vtbl(data: bytes, offset: int) -> dict | None:
    if data[offset : offset + 4] != b"VTBL":
        return None
    length = struct.unpack("<I", data[offset + 4 : offset + 8])[0]
    return {"offset": offset, "length": length}


def format_ppch(record: dict) -> list[str]:
    lines = [f"PPCH at 0x{record['offset']:x} crc={record['crc']} entries={len(record['entries'])}"]
    for entry in record["entries"]:
        lines.append(
            f"  {entry['name']:10} {entry['device']:32} "
            f"offset=0x{entry['offset']:08x} flag=0x{entry['flag']:x} slot={entry['slot']}"
        )
    return lines


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="", help="bootchain dump directory (default: latest under dist/bootchain)")
    args = parser.parse_args(argv)

    root = Path(args.dir) if args.dir else None
    if root is None:
        base = Path("dist") / "bootchain"
        if not base.is_dir():
            print(f"missing {base}; run tools/bootchain_dump.py first", file=sys.stderr)
            return 2
        dirs = [path for path in base.iterdir() if path.is_dir()]
        if not dirs:
            print(f"no dump directories under {base}", file=sys.stderr)
            return 2
        root = max(dirs, key=lambda path: path.name)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    p9 = root / "p9-misc.bin"
    p1 = root / "p1-vendor-boot0.bin"
    p2 = root / "p2-vendor-boot1.bin"

    if p9.is_file():
        data = p9.read_bytes()
        print(f"p9: {p9.name} ({len(data)} bytes)")
        for magic, offset in scan_magics(data):
            print(f"  {magic} at 0x{offset:x}")
        for magic, offset in scan_magics(data):
            if magic == "PPCH":
                record = parse_ppch(data, offset)
                if record:
                    print("\n".join(format_ppch(record)))
                    print()

    for path in (p1, p2):
        if not path.is_file():
            continue
        data = path.read_bytes()
        print(f"{path.name}: {len(data)} bytes")
        for magic, offset in scan_magics(data):
            print(f"  {magic} at 0x{offset:x}")
            if magic == "STBC":
                record = parse_stbc(data, offset)
                if record:
                    print(f"    STBC header={record['header']} slot={record['slot']}")
            elif magic == "VTBL":
                record = parse_vtbl(data, offset)
                if record:
                    print(f"    VTBL length=0x{record['length']:x}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
