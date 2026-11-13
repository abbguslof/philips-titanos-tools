#!/usr/bin/env python3
"""
Parse a Novatek TIMG/PIMG firmware package.

The research package is PH_2K25_ALL_EU_NT72690_TPN256E_V056.002.236.191_upgrade.pkg.
A TIMG container has a 0x120 header and a sequence of PIMG components with
0x488 headers. Compression may be enc=none or enc=gzip. Decompressed
filesystems begin with a 0x1000-byte NFSB header followed by SquashFS.

This tool does not execute the package. It lists, verifies, and optionally
extracts components. It does not bypass the NFSB RSA/SHA-256 layer.

Newer 2023+ Philips Titan OS packages (e.g.
TPN236E_236.006.135.001 `autorun.upg`) use a revised container format,
`TIMGPKGVER40`:

- container header is still 0x120 bytes, but magic is `TIMGPKGVER40` and there
  is no whole-container length/MD5 field at 0x08/0x10; instead a `PPCH`/vertbl
  partition table follows the header and the component region runs to EOF;
- PIMG headers are 0x460 bytes with the length as a **u32 at 0x04**, the MD5
  (16 bytes) at 0x08, name at 0x18 (16 B), target at 0x28 (32 B) and
  compression at 0x48 (16 B); components are back-to-back
  (`next = header + 0x460 + length`), ending exactly at EOF;
- **every component payload is stored vendor-encrypted** (fixed key), so this
  tool cannot decrypt anything; the `compression` field (`none`/`gzip`)
  describes the state *after* decryption, and the PIMG MD5 covers the
  **stored** (encrypted) payload. `unixtract`
  (github.com/theubusu/unixtract) performs the decryption.
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

VER40_CONTAINER_MAGIC = b"TIMGPKGVER40"
VER40_PIMG_HEADER_SIZE = 0x460


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


def parse_pimg_header_ver40(header: bytes) -> dict:
    if len(header) < VER40_PIMG_HEADER_SIZE:
        raise ValueError(f"short VER40 PIMG header: {len(header)} bytes")
    if header[:4] != PIMG_MAGIC:
        raise ValueError("not a PIMG header")
    return {
        "length": struct.unpack_from("<I", header, 0x04)[0],
        "md5": header[0x08:0x18].hex(),
        "name": _cstr(header, 0x18, 16),
        "target": _cstr(header, 0x28, 32),
        "compression": _cstr(header, 0x48, 16),
        "flags": "",  # flags field location unknown in VER40; header is zero-padded
    }


def _ver40_first_pimg_offset(path: Path, file_size: int) -> int:
    """Find the first real VER40 PIMG header.

    The container header region (0x120 .. start of components) holds a
    `PPCH`/vertbl partition table whose length varies. Components are
    back-to-back and end exactly at EOF, so a candidate offset is real when
    walking it with VER40 rules lands on EOF. Payloads may themselves contain
    the bytes `PIMG`, so candidates are validated by walk, not by magic alone.
    """
    data = path.read_bytes()
    start = TIMG_HEADER_SIZE
    while True:
        candidate = data.find(PIMG_MAGIC, start)
        if candidate < 0:
            raise ValueError("no VER40 PIMG component found after the container header")
        try:
            _ver40_walk(data, candidate, file_size)
        except ValueError:
            start = candidate + 1
            continue
        return candidate


def _ver40_walk(data: bytes, offset: int, file_size: int) -> list[Pimg]:
    components: list[Pimg] = []
    index = 0
    while offset < file_size:
        header = data[offset : offset + VER40_PIMG_HEADER_SIZE]
        if len(header) != VER40_PIMG_HEADER_SIZE:
            raise ValueError(f"truncated VER40 PIMG header at 0x{offset:x}")
        if header[:4] != PIMG_MAGIC:
            raise ValueError(f"expected PIMG at 0x{offset:x}, got {header[:4]!r}")
        fields = parse_pimg_header_ver40(header)
        if fields["length"] <= 0 or offset + VER40_PIMG_HEADER_SIZE + fields["length"] > file_size:
            raise ValueError(f"implausible VER40 component {fields['name']!r} at 0x{offset:x}")
        payload_offset = offset + VER40_PIMG_HEADER_SIZE
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
    return components


def parse_timg_ver40(path: Path) -> tuple[dict, list[Pimg]]:
    with path.open("rb") as f:
        header = f.read(TIMG_HEADER_SIZE)
        if len(header) != TIMG_HEADER_SIZE:
            raise ValueError("file is shorter than the TIMG header")
        if header[:12] != VER40_CONTAINER_MAGIC:
            raise ValueError(f"not a VER40 container: {header[:12]!r}")
    file_size = path.stat().st_size
    first = _ver40_first_pimg_offset(path, file_size)
    data = path.read_bytes()
    components = _ver40_walk(data, first, file_size)
    # VER40 has no whole-container MD5 field; the header region is
    # container-header + vertbl partition table. Per-component MD5s are the
    # verification unit (see --verify).
    return {
        "payload_length": None,
        "payload_md5": None,
        "file_size": file_size,
        "component_count": len(components),
        "format": "VER40",
        "components_offset": first,
    }, components


def parse_timg(path: Path) -> tuple[dict, list[Pimg]]:
    with path.open("rb") as f:
        header = f.read(TIMG_HEADER_SIZE)
        if len(header) != TIMG_HEADER_SIZE:
            raise ValueError("file is shorter than the TIMG header")
        if header[:4] != TIMG_MAGIC:
            raise ValueError(f"not a TIMG container: {header[:4]!r}")
        if header[:12] == VER40_CONTAINER_MAGIC:
            return parse_timg_ver40(path)
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
        "format": "classic",
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


def _copy_range(src_file, dst_file, offset: int, length: int) -> None:
    src_file.seek(offset)
    remaining = length
    while remaining:
        chunk = src_file.read(min(1024 * 1024, remaining))
        if not chunk:
            raise ValueError("unexpected EOF while extracting")
        dst_file.write(chunk)
        remaining -= len(chunk)


def extract_component(path: Path, comp: Pimg, output_dir: Path, ver40: bool = False) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = output_dir / f"{comp.index:02d}-{comp.name}.img"
    with path.open("rb") as src, raw.open("wb") as dst:
        _copy_range(src, dst, comp.payload_offset, comp.length)

    if ver40:
        # VER40 stores every payload vendor-encrypted; the MD5 covers the
        # stored (encrypted) bytes.
        actual = stream_md5(raw, 0, raw.stat().st_size)
        if actual != comp.md5:
            raise ValueError(f"{comp.name}: MD5 mismatch ({actual} != {comp.md5})")
        # Keep the stored payload; `unixtract` performs the decryption. The
        # compression label describes the state after decryption.
        print(
            f"note: {comp.name} payload is vendor-encrypted "
            f"(post-decryption compression: {comp.compression!r}); "
            "stored payload kept, decrypt with unixtract"
        )
        return raw
    else:
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


def _verify_components(path: Path, components: list[Pimg]) -> int:
    failures = 0
    for comp in components:
        actual = stream_md5(path, comp.payload_offset, comp.length)
        status = "OK" if actual == comp.md5 else "MISMATCH"
        if status == "MISMATCH":
            failures += 1
        print(f"  {comp.index:>2} {comp.name:<16} stored {comp.md5}, actual {actual} -> {status}")
    if failures:
        print(f"\ncomponent MD5: {failures} MISMATCH(es)")
    else:
        print(f"\ncomponent MD5: all {len(components)} OK")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="List/verify/extract Novatek TIMG packages.")
    parser.add_argument("package", type=Path, help="path to the .pkg")
    parser.add_argument("--verify", action="store_true", help="verify the whole-container MD5 (classic) or per-component MD5s (VER40)")
    parser.add_argument("--extract", metavar="NAME_OR_INDEX", help="extract one component")
    parser.add_argument("-o", "--output", type=Path, default=Path("fw/extracted"), help="extraction directory")
    args = parser.parse_args()

    try:
        meta, components = parse_timg(args.package)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"package: {args.package}")
    print(f"format:  {meta.get('format', 'classic')}")
    print(f"size:    {meta['file_size']} bytes")
    if meta["payload_md5"] is not None:
        print(f"payload: {meta['payload_length']} bytes, MD5 {meta['payload_md5']}")
    else:
        print(f"payload: component region from 0x{meta['components_offset']:x} to EOF (VER40: no container-level MD5)")
    print(f"components: {meta['component_count']}")
    print()
    print(f"{'#':>2}  {'name':<16} {'compression':<10} {'length':>12}  {'target':<28} flags")
    for comp in components:
        print(
            f"{comp.index:>2}  {comp.name:<16} {comp.compression:<10} "
            f"{comp.length:>12}  {comp.target:<28} {comp.flags}"
        )

    if args.verify:
        if meta["payload_md5"] is not None:
            actual = stream_md5(args.package, TIMG_HEADER_SIZE, meta["payload_length"])
            status = "OK" if actual == meta["payload_md5"] else "MISMATCH"
            print(f"\ncontainer MD5: stored {meta['payload_md5']}, actual {actual} -> {status}")
            if actual != meta["payload_md5"]:
                return 1
        else:
            print("\ncomponent MD5s (VER40: verification is per component):")
            return _verify_components(args.package, components)

    if args.extract:
        selected: Optional[Pimg] = None
        for comp in components:
            if args.extract == str(comp.index) or args.extract == comp.name:
                selected = comp
                break
        if selected is None:
            print(f"ERROR: no component named {args.extract!r}", file=sys.stderr)
            return 1
        out = extract_component(
            args.package, selected, args.output, ver40=meta.get("format") == "VER40"
        )
        print(f"\nextracted: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
