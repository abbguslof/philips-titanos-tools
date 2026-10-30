#!/usr/bin/env python3
import os
import unittest

from tools.edid_tool import verify_edid_nvm

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG_EDID_PATH = os.path.join(REPO_ROOT, "samples", "nvm", "nvm_edid.data")


class TestEDIDTool(unittest.TestCase):

    def setUp(self):
        self.assertTrue(
            os.path.exists(ORIG_EDID_PATH),
            f"Original EDID dump not found at {ORIG_EDID_PATH}",
        )
        with open(ORIG_EDID_PATH, "rb") as f:
            self.orig_bytes = f.read()

    def test_original_edid_verification(self):
        """Original factory EDID dump must pass CRC32 verification."""
        ok, stored, calc = verify_edid_nvm(self.orig_bytes)
        self.assertTrue(ok, f"EDID CRC32 failed: stored={stored:08x}, calc={calc:08x}")
        self.assertEqual(stored, 0x2A790D71)

    def test_edid_tamper_detection(self):
        """Corrupting a byte must trigger CRC failure."""
        corrupted = bytearray(self.orig_bytes)
        corrupted[10] ^= 0x01
        ok, stored, calc = verify_edid_nvm(bytes(corrupted))
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
