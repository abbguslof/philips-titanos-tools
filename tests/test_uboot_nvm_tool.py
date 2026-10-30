#!/usr/bin/env python3
import os
import tempfile
import unittest

from tools.uboot_nvm_tool import UBootNVM

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG_NVM_PATH = os.path.join(REPO_ROOT, "samples", "nvm", "nvm_ubootdat.data")


class TestUBootNVMTool(unittest.TestCase):

    def setUp(self):
        self.assertTrue(
            os.path.exists(ORIG_NVM_PATH),
            f"Original dump not found at {ORIG_NVM_PATH}",
        )
        with open(ORIG_NVM_PATH, "rb") as f:
            self.orig_bytes = f.read()

    def test_original_file_verification(self):
        """The original factory dump must pass both inner and outer CRC32 checks."""
        nvm = UBootNVM(self.orig_bytes)
        inner_ok, outer_ok, sin, cin, sout, cout = nvm.verify()
        self.assertTrue(inner_ok, f"Inner CRC failed: stored={sin:08x}, calc={cin:08x}")
        self.assertTrue(outer_ok, f"Outer CRC failed: stored={sout:08x}, calc={cout:08x}")
        self.assertEqual(nvm.part_id, 9)
        self.assertEqual(nvm.hdr_len, 36)
        self.assertIn("board_id", nvm.variables)
        self.assertEqual(nvm.variables["board_id"], "NT72690")
        self.assertEqual(nvm.variables["uart_mode"], "1")

    def test_bit_identical_roundtrip(self):
        """Re-building the binary without edits must produce identical bytes."""
        nvm = UBootNVM(self.orig_bytes)
        rebuilt = nvm.build_binary()
        self.assertEqual(len(rebuilt), len(self.orig_bytes))
        self.assertEqual(rebuilt, self.orig_bytes)

    def test_variable_modification_and_checksum_integrity(self):
        """Modifying a variable must recalculate valid dual CRC32 checksums."""
        nvm = UBootNVM(self.orig_bytes)
        nvm.variables["bootargs"] = "console=ttyS0,115200 init=/bin/sh"
        nvm.var_order.append("bootargs")

        new_data = nvm.build_binary()
        self.assertEqual(len(new_data), len(self.orig_bytes))

        # Re-parse generated binary and verify
        reloaded = UBootNVM(new_data)
        inner_ok, outer_ok, _, _, _, _ = reloaded.verify()
        self.assertTrue(inner_ok, "Recalculated inner CRC must be valid")
        self.assertTrue(outer_ok, "Recalculated outer CRC must be valid")
        self.assertEqual(reloaded.variables["bootargs"], "console=ttyS0,115200 init=/bin/sh")

    def test_variable_deletion(self):
        """Deleting a variable must update the binary cleanly with valid checksums."""
        nvm = UBootNVM(self.orig_bytes)
        self.assertIn("SwitchOffTimer", nvm.variables)

        del nvm.variables["SwitchOffTimer"]
        nvm.var_order.remove("SwitchOffTimer")

        new_data = nvm.build_binary()
        reloaded = UBootNVM(new_data)
        inner_ok, outer_ok, _, _, _, _ = reloaded.verify()
        self.assertTrue(inner_ok)
        self.assertTrue(outer_ok)
        self.assertNotIn("SwitchOffTimer", reloaded.variables)

    def test_tamper_detection(self):
        """Tampering with an environment byte must cause CRC verification failure."""
        corrupted = bytearray(self.orig_bytes)
        # Flip a bit in the environment area (e.g. offset 100)
        corrupted[100] ^= 0xFF
        nvm = UBootNVM(bytes(corrupted))
        inner_ok, outer_ok, _, _, _, _ = nvm.verify()
        self.assertFalse(inner_ok)
        self.assertFalse(outer_ok)


if __name__ == "__main__":
    unittest.main()
