#!/usr/bin/env python3
from __future__ import annotations
import gzip
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from tools.firmware.parse_timg import (
    PIMG_HEADER_SIZE,
    TIMG_HEADER_SIZE,
    extract_component,
    parse_pimg_header,
    parse_timg,
)


def build_pimg(name: str, payload: bytes, compression: str = "enc=none", md5_data: bytes | None = None) -> bytes:
    header = bytearray(PIMG_HEADER_SIZE)
    header[0:4] = b"PIMG"
    struct.pack_into("<Q", header, 0x08, len(payload))
    header[0x10:0x20] = hashlib.md5(md5_data if md5_data is not None else payload).digest()
    header[0x20:0x20 + len(name)] = name.encode()
    header[0x30:0x30 + 4] = b"/dev"
    header[0x70:0x70 + len(compression)] = compression.encode()
    header[0x84:0x84 + 3] = b"RAW"
    return bytes(header) + payload


def build_timg(components: list[bytes]) -> bytes:
    payload = b"".join(components)
    header = bytearray(TIMG_HEADER_SIZE)
    header[0:4] = b"TIMG"
    struct.pack_into("<Q", header, 0x08, len(payload))
    header[0x10:0x20] = hashlib.md5(payload).digest()
    return bytes(header) + payload


class TestTimgParser(unittest.TestCase):
    def test_parse_pimg_header(self):
        blob = build_pimg("fs0", b"hello")
        fields = parse_pimg_header(blob[:PIMG_HEADER_SIZE])
        self.assertEqual(fields["name"], "fs0")
        self.assertEqual(fields["length"], 5)
        self.assertEqual(fields["md5"], hashlib.md5(b"hello").hexdigest())
        self.assertEqual(fields["target"], "/dev")
        self.assertEqual(fields["compression"], "enc=none")
        self.assertEqual(fields["flags"], "RAW")

    def test_parse_and_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "test.pkg"
            pkg.write_bytes(build_timg([build_pimg("fs0", b"hello"), build_pimg("ap0", b"world")]))
            meta, components = parse_timg(pkg)
            self.assertEqual(meta["component_count"], 2)
            self.assertEqual([c.name for c in components], ["fs0", "ap0"])
            out = extract_component(pkg, components[0], Path(tmp) / "out")
            self.assertEqual(out.read_bytes(), b"hello")

    def test_gzip_component_md5_is_over_decompressed_payload(self):
        plain = b"gzip component payload"
        compressed = gzip.compress(plain)
        blob = build_pimg("apext0", compressed, "enc=gzip", md5_data=plain)
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "test.pkg"
            pkg.write_bytes(build_timg([blob]))
            _, components = parse_timg(pkg)
            self.assertEqual(components[0].compression, "enc=gzip")
            out = extract_component(pkg, components[0], Path(tmp) / "out")
            self.assertEqual(out.read_bytes(), plain)


if __name__ == "__main__":
    unittest.main()
