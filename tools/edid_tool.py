#!/usr/bin/env python3
"""
Philips Titan OS / SAM EDID NVM Tool

Inspects, verifies, and recalculates CRC32 checksums for Philips SAM
'nvm_edid.data' files.

Structure:
  - Offset 0x00 - 0x03 : Outer CRC32 (little-endian) covering bytes [0x04 .. EOF]
  - Offset 0x04 - 0x07 : Partition ID (uint32, 50 / 0x32 for edid)
  - Offset 0x08 - 0x0B : Reserved (uint32)
  - Offset 0x0C - 0x0F : Block offset 1 (0x24)
  - Offset 0x18 - 0x1B : Block offset 2 (0x124)
  - Offset 0x1C - 0x1F : Block offset 3 (0x224)
"""

import argparse
import os
import struct
import sys
import zlib


def verify_edid_nvm(data: bytes):
    if len(data) < 4:
        return False, 0, 0
    stored_crc = struct.unpack("<I", data[:4])[0]
    calc_crc = zlib.crc32(data[4:]) & 0xFFFFFFFF
    return (stored_crc == calc_crc), stored_crc, calc_crc


def cmd_verify(args):
    with open(args.file, "rb") as f:
        data = f.read()

    ok, stored, calc = verify_edid_nvm(data)
    status = "OK" if ok else "CORRUPTED"
    print(f"[{status}] {args.file} ({len(data)} bytes)")
    print(f"  CRC32: 0x{stored:08x} (calc: 0x{calc:08x}) -> {'PASS' if ok else 'FAIL'}")

    if not ok:
        sys.exit(1)


def cmd_info(args):
    with open(args.file, "rb") as f:
        data = f.read()

    ok, stored, calc = verify_edid_nvm(data)
    part_id = struct.unpack("<I", data[4:8])[0] if len(data) >= 8 else 0

    print("=== Philips SAM EDID NVM Dump ===")
    print(f"File:         {args.file} ({len(data)} bytes)")
    print(f"Partition ID: {part_id} (0x{part_id:02x})")
    print(f"CRC32:        0x{stored:08x} -> {'VALID' if ok else f'INVALID (calc: 0x{calc:08x})'}")

    # Inspect non-zero segments
    non_zero_count = sum(1 for b in data if b != 0)
    print(f"Non-zero payload bytes: {non_zero_count} / {len(data)}")

    # Check for embedded ASCII strings
    ascii_strings = []
    current = []
    for b in data[4:]:
        if 32 <= b < 127:
            current.append(chr(b))
        else:
            if len(current) >= 4:
                ascii_strings.append("".join(current))
            current = []
    if current and len(current) >= 4:
        ascii_strings.append("".join(current))

    if ascii_strings:
        print("\nDiscovered ASCII/JSON Fragments:")
        for s in ascii_strings:
            print(f"  - {s}")


def cmd_recalc(args):
    with open(args.file, "rb") as f:
        data = bytearray(f.read())

    calc_crc = zlib.crc32(data[4:]) & 0xFFFFFFFF
    struct.pack_into("<I", data, 0, calc_crc)

    out_path = args.output or args.file
    with open(out_path, "wb") as f:
        f.write(data)

    print(f"Updated CRC32 to 0x{calc_crc:08x} and saved to '{out_path}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Philips SAM EDID NVM Checksum & Inspection Tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_verify = subparsers.add_parser("verify", help="Verify outer CRC32 checksum")
    p_verify.add_argument("file", help="Path to nvm_edid.data")
    p_verify.set_defaults(func=cmd_verify)

    p_info = subparsers.add_parser("info", help="Display EDID container information")
    p_info.add_argument("file", help="Path to nvm_edid.data")
    p_info.set_defaults(func=cmd_info)

    p_recalc = subparsers.add_parser("recalc", help="Recalculate CRC32 for modified file")
    p_recalc.add_argument("file", help="Path to input nvm_edid.data")
    p_recalc.add_argument("-o", "--output", help="Output file path (defaults to in-place)")
    p_recalc.set_defaults(func=cmd_recalc)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
