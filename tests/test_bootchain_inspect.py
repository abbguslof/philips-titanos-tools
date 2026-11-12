#!/usr/bin/env python3
from __future__ import annotations
import math
import struct
import sys
import unittest
import zlib
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import bootchain_inspect  # noqa: E402


def make_uimage(payload: bytes, name: str = "Linux", data_crc: int | None = None) -> bytes:
    header = struct.pack(
        ">7I4B",
        0x27051956,
        0,
        0,
        len(payload),
        0x02800000,
        0x02800000,
        zlib.crc32(payload) & 0xFFFFFFFF if data_crc is None else data_crc,
        5,
        22,
        2,
        0,
    ) + name.encode().ljust(32, b"\0")
    hcrc = zlib.crc32(header) & 0xFFFFFFFF
    return header[:4] + struct.pack(">I", hcrc) + header[8:] + payload


class TestBootchainInspect(unittest.TestCase):
    def test_parse_valid_uimage(self):
        payload = b"\0" * 0x38 + b"ARM\x64" + b"\0" * 64
        parsed = bootchain_inspect.parse_uimage(make_uimage(payload))
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["name"], "Linux")
        self.assertEqual(parsed["arch"], "arm64")
        self.assertTrue(parsed["header_crc_ok"])
        self.assertTrue(parsed["data_crc_ok"])
        self.assertIn("arm64-Image", parsed["payload_magic"])
        self.assertEqual(parsed["data_first_16"], payload[:16].hex())

    def test_bad_data_crc_is_reported(self):
        parsed = bootchain_inspect.parse_uimage(make_uimage(b"data", data_crc=1))
        self.assertFalse(parsed["data_crc_ok"])

    def test_non_uimage_returns_none(self):
        self.assertIsNone(bootchain_inspect.parse_uimage(b"not an image"))
        self.assertIsNone(bootchain_inspect.parse_uimage(b""))

    def test_embedded_uimage_is_found(self):
        image = make_uimage(b"payload")
        blob = b"\0" * 100 + image
        found = bootchain_inspect.find_uimages(blob)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["offset"], 100)

    def test_entropy(self):
        self.assertEqual(bootchain_inspect.entropy(b"\0" * 1000), 0.0)
        self.assertAlmostEqual(bootchain_inspect.entropy(bytes(range(256)) * 4), 8.0, places=6)

    def test_known_markers(self):
        record = bootchain_inspect.inspect_file
        self.assertTrue(callable(record))
        # The marker scanner is intentionally a local summary, not a parser.
        self.assertIn(b"UMFG", bootchain_inspect.MARKERS)

    def test_latest_dir(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").mkdir()
            (root / "b").mkdir()
            self.assertEqual(bootchain_inspect.latest_dir(root).name, "b")


if __name__ == "__main__":
    unittest.main()
