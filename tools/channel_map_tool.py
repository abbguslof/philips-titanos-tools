#!/usr/bin/env python3
"""
Philips Titan OS Channel Map & chanLst.bin Integrity Tool

Parses, verifies, recalculates, and manipulates Philips ChannelMap structures
(PhilipsChannelMaps/ChannelMap_100).

Reverse-Engineered Format:
- Prefix (18 bytes): ChannelMap version identifier and header flags.
- Model string: 32-bit Little-Endian length followed by ASCII null-terminated string.
- Records: 32-bit Little-Endian length followed by path string.
  - Files are terminated with a 16-bit Little-Endian CRC-16/MODBUS checksum of the file.
  - Directories (e.g. '/s2channellib/') serve as sub-path prefixes without a CRC.
"""

import argparse
import os
import struct
import sys
from typing import Dict, List, Optional, Tuple


def crc16_modbus(data: bytes) -> int:
    """Computes CRC-16/MODBUS over data bytes."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


class ChannelMapEntry:
    def __init__(self, path: str, is_dir: bool = False, expected_crc: Optional[int] = None):
        self.path = path
        self.is_dir = is_dir
        self.expected_crc = expected_crc
        self.actual_crc: Optional[int] = None
        self.is_valid: bool = False

    def __repr__(self):
        if self.is_dir:
            return f"<ChannelMapDir path='{self.path}'>"
        return f"<ChannelMapFile path='{self.path}' crc=0x{self.expected_crc:04x}>"


class ChannelMap:
    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        if os.path.isfile(self.root_dir) and os.path.basename(self.root_dir) == "chanLst.bin":
            self.chan_lst_bin = self.root_dir
            self.channel_list_dir = os.path.dirname(self.root_dir)
            self.map_dir = os.path.dirname(self.channel_list_dir)
        elif os.path.basename(self.root_dir) == "ChannelList":
            self.channel_list_dir = self.root_dir
            self.map_dir = os.path.dirname(self.root_dir)
            self.chan_lst_bin = os.path.join(self.channel_list_dir, "chanLst.bin")
        elif os.path.exists(os.path.join(self.root_dir, "ChannelList")):
            self.map_dir = self.root_dir
            self.channel_list_dir = os.path.join(self.root_dir, "ChannelList")
            self.chan_lst_bin = os.path.join(self.channel_list_dir, "chanLst.bin")
        else:
            self.map_dir = self.root_dir
            self.channel_list_dir = self.root_dir
            self.chan_lst_bin = os.path.join(self.channel_list_dir, "chanLst.bin")
        self.header_prefix: bytes = b""
        self.model: str = ""
        self.entries: List[ChannelMapEntry] = []

    def parse(self):
        if not os.path.exists(self.chan_lst_bin):
            raise FileNotFoundError(f"chanLst.bin not found at {self.chan_lst_bin}")

        with open(self.chan_lst_bin, "rb") as f:
            data = f.read()

        if len(data) < 22:
            raise ValueError(f"chanLst.bin too small ({len(data)} bytes)")

        # Header prefix: 18 bytes
        self.header_prefix = data[0:18]
        offset = 18

        # Model string: 4-byte LE length + null-terminated string
        model_len = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4
        self.model = data[offset:offset + model_len].rstrip(b"\x00").decode("ascii", errors="replace")
        offset += model_len

        # Parse records
        self.entries = []
        while offset < len(data):
            if offset + 4 > len(data):
                break
            str_len = struct.unpack("<I", data[offset:offset + 4])[0]
            offset += 4
            raw_str = data[offset:offset + str_len]
            path_str = raw_str.rstrip(b"\x00").decode("ascii", errors="replace")
            offset += str_len

            if path_str.endswith("/"):
                # Directory entry (no trailing CRC)
                self.entries.append(ChannelMapEntry(path_str, is_dir=True))
            else:
                # File entry: 2-byte LE CRC-16
                if offset + 2 <= len(data):
                    crc_val = struct.unpack("<H", data[offset:offset + 2])[0]
                    offset += 2
                    self.entries.append(ChannelMapEntry(path_str, is_dir=False, expected_crc=crc_val))
                else:
                    self.entries.append(ChannelMapEntry(path_str, is_dir=False, expected_crc=0))

    def _resolve_file(self, entry_path: str, current_dir: str = "") -> Optional[str]:
        clean_path = entry_path.lstrip("/")
        candidates = [
            os.path.join(self.channel_list_dir, "channellib", clean_path),
            os.path.join(self.channel_list_dir, "s2channellib", clean_path),
            os.path.join(self.channel_list_dir, clean_path),
            os.path.join(self.map_dir, clean_path),
        ]
        if current_dir:
            clean_dir = current_dir.strip("/")
            candidates.insert(0, os.path.join(self.channel_list_dir, clean_dir, clean_path))
            candidates.insert(1, os.path.join(self.map_dir, clean_dir, clean_path))

        for c in candidates:
            if os.path.exists(c) and not os.path.isdir(c):
                return c
        return None

    def verify(self) -> Tuple[bool, List[str]]:
        self.parse()
        all_ok = True
        reports = []
        current_dir = ""

        for entry in self.entries:
            if entry.is_dir:
                current_dir = entry.path
                reports.append(f"DIR:  {entry.path}")
                continue

            file_path = self._resolve_file(entry.path, current_dir)
            if not file_path:
                entry.is_valid = False
                all_ok = False
                reports.append(f"MISSING: {entry.path} (target file not found on disk)")
                continue

            with open(file_path, "rb") as f:
                content = f.read()

            entry.actual_crc = crc16_modbus(content)
            entry.is_valid = (entry.actual_crc == entry.expected_crc)
            if not entry.is_valid:
                all_ok = False
                reports.append(
                    f"FAIL: {entry.path} -> expected CRC 0x{entry.expected_crc:04x}, "
                    f"computed 0x{entry.actual_crc:04x}"
                )
            else:
                reports.append(f"PASS: {entry.path} -> CRC 0x{entry.actual_crc:04x} OK ({file_path})")

        return all_ok, reports

    def recalculate(self, output_file: Optional[str] = None) -> str:
        self.parse()
        current_dir = ""

        # Update expected CRCs for all files
        for entry in self.entries:
            if entry.is_dir:
                current_dir = entry.path
                continue

            file_path = self._resolve_file(entry.path, current_dir)
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    entry.expected_crc = crc16_modbus(f.read())
                entry.actual_crc = entry.expected_crc
                entry.is_valid = True

        # Pack binary chanLst.bin
        out = bytearray()
        out.extend(self.header_prefix)

        # Model string
        model_bytes = self.model.encode("ascii") + b"\x00"
        out.extend(struct.pack("<I", len(model_bytes)))
        out.extend(model_bytes)

        # Entries
        for entry in self.entries:
            path_bytes = entry.path.encode("ascii") + b"\x00"
            out.extend(struct.pack("<I", len(path_bytes)))
            out.extend(path_bytes)
            if not entry.is_dir:
                out.extend(struct.pack("<H", entry.expected_crc or 0))

        dest = output_file or self.chan_lst_bin
        with open(dest, "wb") as f:
            f.write(out)
        return dest


def cmd_verify(args):
    cm = ChannelMap(args.path)
    ok, reports = cm.verify()
    print(f"=== ChannelMap Verification: {cm.map_dir} ===")
    print(f"Model:   {cm.model}")
    print("-" * 60)
    for r in reports:
        print(f"  {r}")
    print("-" * 60)
    if ok:
        print("✓ All channel map CRC-16/MODBUS checksums VALID!")
        sys.exit(0)
    else:
        print("✗ Verification FAILED: CRC mismatch or missing files.")
        sys.exit(1)


def cmd_dump(args):
    cm = ChannelMap(args.path)
    cm.parse()
    print(f"=== ChannelMap Dump: {cm.map_dir} ===")
    print(f"Model:   {cm.model}")
    print(f"Entries: {len(cm.entries)}")
    print("-" * 60)
    current_dir = ""
    for i, e in enumerate(cm.entries):
        if e.is_dir:
            current_dir = e.path
            print(f"[{i}] DIR:  {e.path}")
        else:
            resolved = cm._resolve_file(e.path, current_dir) or "Not found"
            print(f"[{i}] FILE: {e.path} -> CRC: 0x{e.expected_crc:04x} (Resolved: {resolved})")


def cmd_recalc(args):
    cm = ChannelMap(args.path)
    dest = cm.recalculate(args.output)
    print(f"✓ Recalculated CRC-16/MODBUS checksums and saved to {dest}")


def main():
    parser = argparse.ArgumentParser(
        description="Philips Titan OS Channel Map & chanLst.bin Integrity Tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # verify
    p_v = subparsers.add_parser("verify", help="Verify CRC16/MODBUS checksums of channel map")
    p_v.add_argument("path", help="Path to ChannelMap_100 directory or chanLst.bin")
    p_v.set_defaults(func=cmd_verify)

    # dump
    p_d = subparsers.add_parser("dump", help="Dump records and paths from chanLst.bin")
    p_d.add_argument("path", help="Path to ChannelMap_100 directory or chanLst.bin")
    p_d.set_defaults(func=cmd_dump)

    # recalculate
    p_r = subparsers.add_parser("recalculate", help="Recalculate checksums and write chanLst.bin")
    p_r.add_argument("path", help="Path to ChannelMap_100 directory or chanLst.bin")
    p_r.add_argument("-o", "--output", help="Optional output path for modified chanLst.bin")
    p_r.set_defaults(func=cmd_recalc)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
