#!/usr/bin/env python3
"""
Philips Titan OS / Novatek NT72690 U-Boot NVM Tool

Inspects, verifies, modifies, diffs, exports, and recalculates dual CRC32 checksums
for Philips Service Alignment Mode (SAM) 'nvm_ubootdat.data' files.

Dual Checksum Architecture:
  - Offset 0x00 - 0x03 : Outer CRC32 (little-endian) covering bytes [0x04 .. EOF]
  - Offset 0x04 - 0x07 : Partition ID (uint32, 9 for ubootdat)
  - Offset 0x08 - 0x0B : Header Size (uint32, 0x24 = 36 bytes)
  - Offset 0x0C - 0x23 : Reserved padding (24 zero bytes)
  - Offset 0x24 - 0x27 : Inner CRC32 (little-endian) covering bytes [0x28 .. EOF]
  - Offset 0x28 - 0x2B : Flash payload header / sub-CRC
  - Offset 0x2C - EOF  : Null-delimited ASCII 'key=value' environment strings,
                         terminated by double-null and padded with zeroes.
"""

import argparse
import difflib
import os
import struct
import sys
import zlib
from typing import Dict, List, Optional, Tuple

HEADER_MAGIC_SIZE = 0x24  # 36 bytes
INNER_PAYLOAD_OFFSET = 0x28  # 40 bytes
SUB_HEADER_SIZE = 4  # 4 bytes for payload sub-header (offset 0x28..0x2C)
ENV_STRINGS_OFFSET = INNER_PAYLOAD_OFFSET + SUB_HEADER_SIZE  # 0x2C (44 bytes)


class UBootNVM:
    """Represents a Philips Titan OS U-Boot NVM data binary."""

    def __init__(self, raw_bytes: bytes):
        if len(raw_bytes) < ENV_STRINGS_OFFSET:
            raise ValueError(
                f"Binary too small: {len(raw_bytes)} bytes (minimum {ENV_STRINGS_OFFSET})"
            )
        self.raw_size = len(raw_bytes)
        self.header_prefix = raw_bytes[4:HEADER_MAGIC_SIZE]
        self.outer_crc_stored = struct.unpack("<I", raw_bytes[0:4])[0]
        self.part_id = struct.unpack("<I", raw_bytes[4:8])[0]
        self.hdr_len = struct.unpack("<I", raw_bytes[8:12])[0]
        self.inner_crc_stored = struct.unpack("<I", raw_bytes[0x24:0x28])[0]

        # Inner payload covers 0x28 to EOF
        self.payload_raw = raw_bytes[INNER_PAYLOAD_OFFSET:]
        self.sub_header = self.payload_raw[:SUB_HEADER_SIZE]

        # Environment strings start at 0x2C
        env_raw = raw_bytes[ENV_STRINGS_OFFSET:]
        end_idx = env_raw.find(b"\x00\x00")
        if end_idx == -1:
            # Fallback to end of file if no double null found
            end_idx = len(env_raw)
        self.env_block = env_raw[:end_idx + 1]

        # Parse key=value pairs preserving order
        self.variables: Dict[str, str] = {}
        self.var_order: List[str] = []
        for item in self.env_block.split(b"\x00"):
            if not item:
                continue
            decoded = item.decode("utf-8", errors="replace")
            if "=" in decoded:
                k, v = decoded.split("=", 1)
                self.variables[k] = v
                self.var_order.append(k)
            else:
                self.variables[decoded] = ""
                self.var_order.append(decoded)

    @classmethod
    def from_file(cls, path: str) -> "UBootNVM":
        with open(path, "rb") as f:
            return cls(f.read())

    def verify(self) -> Tuple[bool, bool, int, int, int, int]:
        """
        Calculates and verifies inner and outer CRC32 checksums.
        Returns:
            (inner_ok, outer_ok, stored_inner, calc_inner, stored_outer, calc_outer)
        """
        calc_inner = zlib.crc32(self.payload_raw) & 0xFFFFFFFF
        inner_ok = calc_inner == self.inner_crc_stored

        # Reconstruct body for outer CRC
        body = (
            self.header_prefix
            + struct.pack("<I", self.inner_crc_stored)
            + self.payload_raw
        )
        calc_outer = zlib.crc32(body) & 0xFFFFFFFF
        outer_ok = calc_outer == self.outer_crc_stored

        return inner_ok, outer_ok, self.inner_crc_stored, calc_inner, self.outer_crc_stored, calc_outer

    def build_binary(self) -> bytes:
        """
        Re-encodes all variables into environment block, pads to original size,
        recalculates inner CRC32 and outer CRC32, and returns the binary.
        """
        lines = []
        for k in self.var_order:
            v = self.variables[k]
            lines.append(f"{k}={v}".encode("utf-8"))

        env_encoded = b"\x00".join(lines) + b"\x00\x00"
        required_len = SUB_HEADER_SIZE + len(env_encoded)
        target_payload_len = self.raw_size - INNER_PAYLOAD_OFFSET

        if required_len > target_payload_len:
            raise ValueError(
                f"Environment size ({required_len} bytes) exceeds available payload partition ({target_payload_len} bytes)."
            )

        pad_len = target_payload_len - required_len
        new_payload = self.sub_header + env_encoded + (b"\x00" * pad_len)

        # Recalculate Inner CRC32 over payload
        new_inner_crc = zlib.crc32(new_payload) & 0xFFFFFFFF
        new_inner_bytes = struct.pack("<I", new_inner_crc)

        # Recalculate Outer CRC32 over [header_prefix + inner_crc + payload]
        body = self.header_prefix + new_inner_bytes + new_payload
        new_outer_crc = zlib.crc32(body) & 0xFFFFFFFF
        new_outer_bytes = struct.pack("<I", new_outer_crc)

        return new_outer_bytes + body

    def save(self, path: str) -> None:
        """Writes the updated binary to path."""
        data = self.build_binary()
        with open(path, "wb") as f:
            f.write(data)


def cmd_dump(args):
    nvm = UBootNVM.from_file(args.file)
    inner_ok, outer_ok, sin, cin, sout, cout = nvm.verify()

    print(f"=== Philips Titan OS U-Boot NVM Dump ===")
    print(f"File:            {args.file} ({nvm.raw_size} bytes)")
    print(f"Partition ID:    {nvm.part_id} (0x{nvm.part_id:02x})")
    print(f"Header Length:   {nvm.hdr_len} (0x{nvm.hdr_len:02x})")
    print(
        f"Inner CRC32:     0x{sin:08x} -> {'VALID' if inner_ok else f'INVALID (calc: 0x{cin:08x})'}"
    )
    print(
        f"Outer CRC32:     0x{sout:08x} -> {'VALID' if outer_ok else f'INVALID (calc: 0x{cout:08x})'}"
    )
    print(f"Total Variables: {len(nvm.variables)}")
    print("-" * 50)

    for k in nvm.var_order:
        v = nvm.variables[k]
        if args.search:
            if args.search.lower() not in k.lower() and args.search.lower() not in v.lower():
                continue
        print(f"{k}={v}")


def cmd_verify(args):
    nvm = UBootNVM.from_file(args.file)
    inner_ok, outer_ok, sin, cin, sout, cout = nvm.verify()

    status = "OK" if (inner_ok and outer_ok) else "CORRUPTED"
    print(f"[{status}] {args.file}")
    print(f"  Inner CRC32: 0x{sin:08x} (calc: 0x{cin:08x}) -> {'PASS' if inner_ok else 'FAIL'}")
    print(f"  Outer CRC32: 0x{sout:08x} (calc: 0x{cout:08x}) -> {'PASS' if outer_ok else 'FAIL'}")

    if not (inner_ok and outer_ok):
        sys.exit(1)


def cmd_get(args):
    nvm = UBootNVM.from_file(args.file)
    if args.key in nvm.variables:
        print(nvm.variables[args.key])
    else:
        print(f"Error: Variable '{args.key}' not found.", file=sys.stderr)
        sys.exit(1)


def cmd_set(args):
    nvm = UBootNVM.from_file(args.file)
    out_path = args.output or args.file

    modified_count = 0
    for kv in args.assignments:
        if "=" not in kv:
            print(f"Error: Invalid assignment '{kv}'. Must be in KEY=VALUE format.", file=sys.stderr)
            sys.exit(1)
        k, v = kv.split("=", 1)
        if k not in nvm.var_order:
            nvm.var_order.append(k)
        nvm.variables[k] = v
        print(f"[SET] {k} = {v}")
        modified_count += 1

    if modified_count > 0:
        nvm.save(out_path)
        print(f"Successfully saved {modified_count} variable(s) to '{out_path}'.")
        print("Recalculated dual CRC32 checksums:")
        new_nvm = UBootNVM.from_file(out_path)
        in_ok, out_ok, sin, cin, sout, cout = new_nvm.verify()
        print(f"  Inner CRC32: 0x{sin:08x} ({'VALID' if in_ok else 'INVALID'})")
        print(f"  Outer CRC32: 0x{sout:08x} ({'VALID' if out_ok else 'INVALID'})")


def cmd_delete(args):
    nvm = UBootNVM.from_file(args.file)
    out_path = args.output or args.file

    if args.key not in nvm.variables:
        print(f"Error: Variable '{args.key}' does not exist.", file=sys.stderr)
        sys.exit(1)

    del nvm.variables[args.key]
    nvm.var_order.remove(args.key)
    nvm.save(out_path)
    print(f"[DELETED] {args.key} from '{out_path}'.")


def cmd_diff(args):
    nvm1 = UBootNVM.from_file(args.file1)
    nvm2 = UBootNVM.from_file(args.file2)

    lines1 = [f"{k}={nvm1.variables[k]}\n" for k in nvm1.var_order]
    lines2 = [f"{k}={nvm2.variables[k]}\n" for k in nvm2.var_order]

    diff = difflib.unified_diff(
        lines1, lines2, fromfile=args.file1, tofile=args.file2, lineterm=""
    )
    diff_text = "\n".join(diff)
    if not diff_text.strip():
        print("No differences found.")
    else:
        print(diff_text)


def cmd_export(args):
    nvm = UBootNVM.from_file(args.file)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("# Philips Titan OS / Novatek U-Boot Environment Export\n")
        f.write(f"# Source: {args.file}\n\n")
        for k in nvm.var_order:
            f.write(f"{k}={nvm.variables[k]}\n")
    print(f"Exported {len(nvm.variables)} variables to '{args.output}'.")


def cmd_import(args):
    template = UBootNVM.from_file(args.template)
    with open(args.env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_vars = {}
    new_order = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            new_vars[k] = v
            new_order.append(k)

    template.variables = new_vars
    template.var_order = new_order
    template.save(args.output)
    print(
        f"Imported {len(new_vars)} variables from '{args.env_file}' and generated '{args.output}'."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Philips Titan OS U-Boot NVM Checksum & Environment Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Dump
    p_dump = subparsers.add_parser("dump", help="Dump all environment variables and headers")
    p_dump.add_argument("file", help="Path to nvm_ubootdat.data")
    p_dump.add_argument("-s", "--search", help="Filter variables by name or value")
    p_dump.set_defaults(func=cmd_dump)

    # Verify
    p_verify = subparsers.add_parser("verify", help="Verify dual CRC32 checksums")
    p_verify.add_argument("file", help="Path to nvm_ubootdat.data")
    p_verify.set_defaults(func=cmd_verify)

    # Get
    p_get = subparsers.add_parser("get", help="Get a single variable value")
    p_get.add_argument("file", help="Path to nvm_ubootdat.data")
    p_get.add_argument("key", help="Variable name")
    p_get.set_defaults(func=cmd_get)

    # Set
    p_set = subparsers.add_parser("set", help="Set or add variables and recalculate checksums")
    p_set.add_argument("file", help="Path to source nvm_ubootdat.data")
    p_set.add_argument(
        "assignments", nargs="+", help="Variable assignments in KEY=VALUE format"
    )
    p_set.add_argument(
        "-o", "--output", help="Output file path (defaults to overwriting input file)"
    )
    p_set.set_defaults(func=cmd_set)

    # Delete
    p_del = subparsers.add_parser("delete", help="Delete a variable and recalculate checksums")
    p_del.add_argument("file", help="Path to source nvm_ubootdat.data")
    p_del.add_argument("key", help="Variable name to remove")
    p_del.add_argument("-o", "--output", help="Output file path")
    p_del.set_defaults(func=cmd_delete)

    # Diff
    p_diff = subparsers.add_parser("diff", help="Diff variables between two NVM dump files")
    p_diff.add_argument("file1", help="First NVM file")
    p_diff.add_argument("file2", help="Second NVM file")
    p_diff.set_defaults(func=cmd_diff)

    # Export
    p_exp = subparsers.add_parser("export", help="Export environment variables to text file")
    p_exp.add_argument("file", help="Path to nvm_ubootdat.data")
    p_exp.add_argument("output", help="Destination text file path (.env)")
    p_exp.set_defaults(func=cmd_export)

    # Import
    p_imp = subparsers.add_parser("import", help="Build NVM binary from text file using template")
    p_imp.add_argument("env_file", help="Source key-value text file")
    p_imp.add_argument("-t", "--template", required=True, help="Reference nvm_ubootdat.data")
    p_imp.add_argument("-o", "--output", required=True, help="Destination NVM binary")
    p_imp.set_defaults(func=cmd_import)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
