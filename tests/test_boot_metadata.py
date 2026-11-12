#!/usr/bin/env python3
import struct
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import boot_metadata  # noqa: E402


class TestBootMetadata(unittest.TestCase):
    def test_ppch_entries(self):
        table = bytearray(b"PPCH" + b"\x00\x00\x00\x00")
        table += b"uboot".ljust(16, b"\0")
        table += b"/dev/nvt-part-name/boot0".ljust(32, b"\0")
        table += struct.pack("<III", 0x100000, 1, 0)
        table += b"vertbl".ljust(16, b"\0")
        table += b"/dev/nvt-part-name/boot0".ljust(32, b"\0")
        table += struct.pack("<III", 0xE7EE00, 1, 0)
        record = boot_metadata.parse_ppch(bytes(table), 0)
        self.assertIsNotNone(record)
        self.assertEqual(len(record["entries"]), 2)
        self.assertEqual(record["entries"][0]["name"], "uboot")
        self.assertEqual(record["entries"][0]["offset"], 0x100000)
        self.assertEqual(record["entries"][1]["name"], "vertbl")
        self.assertEqual(record["entries"][1]["offset"], 0xE7EE00)

    def test_stbc_slot(self):
        data = bytearray(0x210)
        data[0:4] = b"STBC"
        data[4:8] = struct.pack("<I", 1)
        data[0x200:0x204] = b"UMFG"
        data[0x204:0x208] = struct.pack("<I", 1)
        record = boot_metadata.parse_stbc(bytes(data), 0)
        self.assertIsNotNone(record)
        self.assertEqual(record["slot"], 1)

    def test_vtbl_length(self):
        data = b"VTBL" + struct.pack("<I", 0x224) + b"\0" * 32
        record = boot_metadata.parse_vtbl(data, 0)
        self.assertIsNotNone(record)
        self.assertEqual(record["length"], 0x224)

    def test_scan_magics(self):
        data = b"\0" * 16 + b"DBFG" + b"\0" * 16 + b"PPCH" + b"\0" * 16
        found = boot_metadata.scan_magics(data)
        self.assertEqual(found, [("DBFG", 16), ("PPCH", 36)])

    def test_wrong_magic(self):
        self.assertIsNone(boot_metadata.parse_ppch(b"NOPE", 0))
        self.assertIsNone(boot_metadata.parse_stbc(b"NOPE", 0))
        self.assertIsNone(boot_metadata.parse_vtbl(b"NOPE", 0))


if __name__ == "__main__":
    unittest.main()
