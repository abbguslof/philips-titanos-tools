#!/usr/bin/env python3
"""
Parse a Novatek TIMG/PIMG firmware package.

The research package is PH_2K25_ALL_EU_NT72690_TPN256E_V056.002.236.191_upgrade.pkg.
A TIMG container has a 0x120 header and a sequence of PIMG components with
0x488 headers. Compression may be enc=none or enc=gzip. Decompressed
filesystems begin with a 0x1000-byte NFSB header followed by SquashFS.

This tool does not execute the package. It lists, verifies, and optionally
extracts components. It does not bypass the NFSB RSA/SHA-256 layer.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

TIMG_MAGIC = b"TIMG"
PIMG_MAGIC = b"PIMG"
TIMG_HEADER_SIZE = 0x120
PIMG_HEADER_SIZE = 0x488
NFSB_HEADER_SIZE = 0x1000


@dataclass
class Pimg:
    index: int
    offset: int
    payload_offset: int
    length: int
    md5: str
    name: str
    target: str
    compression: str
    flags: str


def _cstr(buf: bytes, offset: int, size: int) -> str:
    raw = buf[offset : offset + size].split(b"\x00", 1)[0]
    return raw.decode("utf-8", errors="replace").strip()


def parse_pimg_header(header: bytes) -> dict:
    if len(header) < PIMG_HEADER_SIZE:
        raise ValueError(f"short PIMG header: {len(header)} bytes")
    if header[:4] != PIMG_MAGIC:
        raise ValueError("not a PIMG header")
    return {
        "length": struct.unpack_from("<Q", header, 0x08)[0],
        "md5": header[0x10:0x20].hex(),
        "name": _cstr(header, 0x20, 32),
        "target": _cstr(header, 0x30, 64),
        "compression": _cstr(header, 0x70, 16),
        "flags": _cstr(header, 0x84, 32),
    }


def parse_timg(path: Path) -> tuple[dict, list[Pimg]]:
    with path.open("rb") as f:
        header = f.read(TIMG_HEADER_SIZE)
        if len(header) != TIMG_HEADER_SIZE:
            raise ValueError("file is shorter than the TIMG header")
        if header[:4] != TIMG_MAGIC:
            raise ValueError(f"not a TIMG container: {header[:4]!r}")
        payload_length = struct.unpack_from("<Q", header, 0x08)[0]
        payload_md5 = header[0x10:0x20].hex()
        total = TIMG_HEADER_SIZE + payload_length
        file_size = path.stat().st_size
        if file_size < total:
            raise ValueError(f"truncated container: {file_size} < {total}")

        components: list[Pimg] = []
        offset = TIMG_HEADER_SIZE
        index = 0
        while offset < total:
            f.seek(offset)
            pimg_header = f.read(PIMG_HEADER_SIZE)
            if len(pimg_header) != PIMG_HEADER_SIZE:
                raise ValueError(f"truncated PIMG header at 0x{offset:x}")
            if pimg_header[:4] != PIMG_MAGIC:
                raise ValueError(f"expected PIMG at 0x{offset:x}, got {pimg_header[:4]!r}")
            fields = parse_pimg_header(pimg_header)
            payload_offset = offset + PIMG_HEADER_SIZE
            if payload_offset + fields["length"] > file_size:
                raise ValueError(f"component {fields['name']} payload exceeds file size")
            components.append(
                Pimg(
                    index=index,
                    offset=offset,
                    payload_offset=payload_offset,
                    length=fields["length"],
                    md5=fields["md5"],
                    name=fields["name"],
                    target=fields["target"],
                    compression=fields["compression"],
                    flags=fields["flags"],
                )
            )
            offset = payload_offset + fields["length"]
            index += 1
        if offset != total:
            raise ValueError(f"component walk ended at 0x{offset:x}, expected 0x{total:x}")
    return {
        "payload_length": payload_length,
        "payload_md5": payload_md5,
        "file_size": file_size,
        "component_count": len(components),
    }, components


def stream_md5(path: Path, offset: int, length: int) -> str:
    digest = hashlib.md5()
    with path.open("rb") as f:
        f.seek(offset)
        remaining = length
        while remaining:
            chunk = f.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("unexpected EOF while hashing")
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.hexdigest()


def extract_component(path: Path, comp: Pimg, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = output_dir / f"{comp.index:02d}-{comp.name}.img"
    with path.open("rb") as src, raw.open("wb") as dst:
        src.seek(comp.payload_offset)
        remaining = comp.length
        while remaining:
            chunk = src.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("unexpected EOF while extracting")
            dst.write(chunk)
            remaining -= len(chunk)
    if "gzip" in comp.compression:
        decompressed = output_dir / f"{comp.index:02d}-{comp.name}.raw"
        with gzip.open(raw, "rb") as src, decompressed.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
        raw.unlink()
        raw = decompressed

    # The PIMG MD5 covers the component payload after decompression.
    actual = stream_md5(raw, 0, raw.stat().st_size)
    if actual != comp.md5:
        raise ValueError(f"{comp.name}: MD5 mismatch ({actual} != {comp.md5})")

    with raw.open("rb") as f:
        head = f.read(4)
    if head == b"NFSB":
        sqsh = output_dir / f"{comp.index:02d}-{comp.name}.sqsh"
        with raw.open("rb") as src, sqsh.open("wb") as dst:
            src.seek(NFSB_HEADER_SIZE)
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
        raw.unlink()
        return sqsh
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description="List/verify/extract Novatek TIMG packages.")
    parser.add_argument("package", type=Path, help="path to the .pkg")
    parser.add_argument("--verify", action="store_true", help="verify the whole-container MD5")
    parser.add_argument("--extract", metavar="NAME_OR_INDEX", help="extract one component")
    parser.add_argument("-o", "--output", type=Path, default=Path("fw/extracted"), help="extraction directory")
    args = parser.parse_args()

    try:
        meta, components = parse_timg(args.package)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"package: {args.package}")
    print(f"size:    {meta['file_size']} bytes")
    print(f"payload: {meta['payload_length']} bytes, MD5 {meta['payload_md5']}")
    print(f"components: {meta['component_count']}")
    print()
    print(f"{'#':>2}  {'name':<16} {'compression':<10} {'length':>12}  {'target':<28} flags")
    for comp in components:
        print(
            f"{comp.index:>2}  {comp.name:<16} {comp.compression:<10} "
            f"{comp.length:>12}  {comp.target:<28} {comp.flags}"
        )

    if args.verify:
        actual = stream_md5(args.package, TIMG_HEADER_SIZE, meta["payload_length"])
        status = "OK" if actual == meta["payload_md5"] else "MISMATCH"
        print(f"\ncontainer MD5: stored {meta['payload_md5']}, actual {actual} -> {status}")
        if actual != meta["payload_md5"]:
            return 1

    if args.extract:
        selected: Optional[Pimg] = None
        for comp in components:
            if args.extract == str(comp.index) or args.extract == comp.name:
                selected = comp
                break
        if selected is None:
            print(f"ERROR: no component named {args.extract!r}", file=sys.stderr)
            return 1
        out = extract_component(args.package, selected, args.output)
        print(f"\nextracted: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
