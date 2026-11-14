#!/usr/bin/env python3
from __future__ import annotations
import gzip
import hashlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from tools.firmware.parse_timg import (
    PIMG_HEADER_SIZE,
    TIMG_HEADER_SIZE,
    VER40_PIMG_HEADER_SIZE,
    extract_component,
    main,
    parse_pimg_header,
    parse_timg,
)


def build_ver40_pimg(name: str, stored_payload: bytes, compression: str = "gzip") -> bytes:
    header = bytearray(VER40_PIMG_HEADER_SIZE)
    header[0:4] = b"PIMG"
    struct.pack_into("<I", header, 0x04, len(stored_payload))
    header[0x08:0x18] = hashlib.md5(stored_payload).digest()
    header[0x18:0x18 + len(name)] = name.encode()
    header[0x28:0x28 + 8] = b"/dev/nvt"  # target prefix, VER40 style
    header[0x48:0x48 + len(compression)] = compression.encode()
    return bytes(header) + stored_payload


def build_ver40_timg(components: list[bytes]) -> bytes:
    # 0x120 container header (magic TIMGPKGVER40), then a PPCH/vertbl table
    # region, then back-to-back components running to EOF.
    header = bytearray(TIMG_HEADER_SIZE)
    header[0:12] = b"TIMGPKGVER40"
    vertbl = bytearray(0x720 - TIMG_HEADER_SIZE)
    vertbl[0:4] = b"PPCH"
    vertbl[0x100:0x104] = b"PIMG"  # decoy: a PIMG magic inside the vertbl must not be treated as a component
    return bytes(header) + bytes(vertbl) + b"".join(components)


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


class TestVer40Parser(unittest.TestCase):
    def test_parse_ver40(self):
        stored_a = b"\xde\xad\xbe\xef" * 8
        stored_b = b"\x01\x02\x03" * 11
        blob = build_ver40_timg(
            [build_ver40_pimg("fs", stored_a, "gzip"), build_ver40_pimg("kernel", stored_b, "none")]
        )
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "test.upg"
            pkg.write_bytes(blob)
            meta, components = parse_timg(pkg)
            self.assertEqual(meta["format"], "VER40")
            self.assertEqual(meta["component_count"], 2)
            self.assertEqual([c.name for c in components], ["fs", "kernel"])
            self.assertEqual([c.compression for c in components], ["gzip", "none"])
            self.assertEqual(components[0].md5, hashlib.md5(stored_a).hexdigest())
            self.assertIsNone(meta["payload_md5"])

    def test_extract_ver40_md5_is_over_stored_payload(self):
        stored = b"stored-encrypted-bytes"
        blob = build_ver40_timg([build_ver40_pimg("fs", stored, "gzip")])
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "test.upg"
            pkg.write_bytes(blob)
            _, components = parse_timg(pkg)
            out = extract_component(pkg, components[0], Path(tmp) / "out", ver40=True)
            # stored payload is kept as-is (vendor-encrypted, no decrypt here)
            self.assertEqual(out.read_bytes(), stored)

    def test_ver40_decoy_pimg_in_vertbl_is_skipped(self):
        blob = build_ver40_timg([build_ver40_pimg("fs", b"payload")])
        # the decoy lives in the vertbl region (see build_ver40_timg); parsing
        # must start at the first *valid* component, not the first magic
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "test.upg"
            pkg.write_bytes(blob)
            meta, components = parse_timg(pkg)
            self.assertEqual(meta["component_count"], 1)
            self.assertEqual(components[0].name, "fs")

    def test_verify_then_extract_in_one_invocation(self):
        stored = b"stored-encrypted-bytes"
        blob = build_ver40_timg([build_ver40_pimg("fs", stored, "gzip")])
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "test.upg"
            pkg.write_bytes(blob)
            out = Path(tmp) / "out"
            argv = sys.argv
            try:
                sys.argv = [
                    "parse_timg.py",
                    str(pkg),
                    "--verify",
                    "--extract",
                    "fs",
                    "-o",
                    str(out),
                ]
                self.assertEqual(main(), 0)
            finally:
                sys.argv = argv
            self.assertEqual((out / "00-fs.img").read_bytes(), stored)


if __name__ == "__main__":
    unittest.main()
