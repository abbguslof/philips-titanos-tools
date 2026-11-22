from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from tools import nfsb_verity


def _header(nblocks: int, salt: bytes, *, magic: bytes = b"NFSB") -> bytearray:
    header = bytearray(nfsb_verity.HEADER_SIZE)
    header[0:4] = magic
    header[0x04] = 3
    header[0x05] = 1
    struct.pack_into(">I", header, nfsb_verity.START_SECTOR, 8)
    struct.pack_into(">I", header, nfsb_verity.DATA_LEN_SECTORS, nblocks * 8)
    struct.pack_into(">I", header, nfsb_verity.DATA_BLOCKS, nblocks)
    struct.pack_into(">I", header, nfsb_verity.DATA_BLOCK_SIZE, 4096)
    struct.pack_into(">I", header, nfsb_verity.HASH_BLOCK_SIZE, 4096)
    header[nfsb_verity.ALGORITHM : nfsb_verity.ALGORITHM + 6] = b"sha256"
    salt_hex = salt.hex().encode("ascii")
    header[nfsb_verity.SALT : nfsb_verity.SALT + len(salt_hex)] = salt_hex
    header[nfsb_verity.DIGEST : nfsb_verity.DIGEST + 64] = b"0" * 64
    return header


def _data(nblocks: int) -> bytes:
    return bytes((i * 7 + 3) & 0xFF for i in range(nblocks * 4096))


def _image(nblocks: int, salt: bytes, data: bytes | None = None) -> bytes:
    payload = _data(nblocks) if data is None else data
    raw = bytes(_header(nblocks, salt)) + payload
    return nfsb_verity.rebuild(raw)


class NfsbVerityTests(unittest.TestCase):
    def test_known_root_one_block(self):
        salt = bytes(range(32))
        data = b"\x5a" * 4096
        raw = bytes(_header(1, salt)) + data
        header = nfsb_verity.parse_header(raw)
        root, tree, levels = nfsb_verity.build_tree(raw, header)
        self.assertEqual(levels, [])
        self.assertEqual(tree, b"")
        self.assertEqual(
            root.hex(),
            "77b4e5c38109ab107e5782e3c637a426511e61782814392b9995737413f8be70",
        )

    def test_single_block_round_trip(self):
        image = _image(1, bytes(range(32)))
        result = nfsb_verity.verify(image)
        self.assertTrue(result.ok)
        self.assertEqual(result.blocks_per_level, [])
        self.assertEqual(len(image), nfsb_verity.HEADER_SIZE + 4096)
        modified = bytearray(image)
        modified[nfsb_verity.HEADER_SIZE] ^= 0xFF
        self.assertFalse(nfsb_verity.verify(bytes(modified)).ok)
        rebuilt = nfsb_verity.rebuild(bytes(modified))
        self.assertTrue(nfsb_verity.verify(rebuilt).ok)

    def test_verify_valid_image(self):
        result = nfsb_verity.verify(_image(4, bytes(range(32))))
        self.assertTrue(result.ok)
        self.assertEqual(result.blocks_per_level, [1])

    def test_verify_two_levels(self):
        result = nfsb_verity.verify(_image(130, bytes(range(32))))
        self.assertTrue(result.ok)
        self.assertEqual(result.blocks_per_level, [2, 1])

    def test_verify_detects_modified_block(self):
        image = bytearray(_image(130, bytes(range(32))))
        image[nfsb_verity.HEADER_SIZE + 100 * 4096] ^= 0xFF
        result = nfsb_verity.verify(bytes(image))
        self.assertFalse(result.root_ok)
        self.assertFalse(result.tree_ok)
        self.assertFalse(result.ok)

    def test_rebuild_accepts_modified_block(self):
        stock = _image(130, bytes(range(32)))
        modified = bytearray(stock)
        offset = nfsb_verity.HEADER_SIZE + 100 * 4096
        modified[offset : offset + 8] = b"MODIFIED"
        self.assertFalse(nfsb_verity.verify(bytes(modified)).ok)

        rebuilt = nfsb_verity.rebuild(bytes(modified))
        result = nfsb_verity.verify(rebuilt)
        self.assertTrue(result.ok)
        self.assertNotEqual(
            result.computed_root,
            nfsb_verity.verify(stock).computed_root,
        )
        self.assertEqual(rebuilt[offset : offset + 8], b"MODIFIED")

    def test_rejects_non_nfsb_magic(self):
        raw = bytes(_header(1, bytes(range(32)), magic=b"XXXX")) + b"\0" * 4096
        with self.assertRaises(nfsb_verity.NfsbError):
            nfsb_verity.verify(raw)

    def test_rejects_short_data(self):
        raw = bytes(_header(2, bytes(range(32)))) + b"\0" * 4096
        with self.assertRaises(nfsb_verity.NfsbError):
            nfsb_verity.verify(raw)

    def test_cli_rebuild_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "in.img"
            output = Path(tmp) / "out.img"
            source.write_bytes(_image(4, bytes(range(32))))
            self.assertEqual(
                nfsb_verity.main(
                    ["rebuild", str(source), "--output", str(output)]
                ),
                0,
            )
            self.assertTrue(nfsb_verity.verify(output.read_bytes()).ok)
            self.assertEqual(
                nfsb_verity.main(
                    ["rebuild", str(source), "--output", str(output)]
                ),
                2,
            )

    def test_cli_rejects_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "in.img"
            source.write_bytes(_image(4, bytes(range(32))))
            self.assertEqual(
                nfsb_verity.main(
                    ["rebuild", str(source), "--output", str(source)]
                ),
                2,
            )


if __name__ == "__main__":
    unittest.main()
