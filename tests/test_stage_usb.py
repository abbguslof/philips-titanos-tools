#!/usr/bin/env python3
import os
import shutil
import tempfile
import unittest

from tools.stage_usb import stage_drive
from tools.uboot_nvm_tool import UBootNVM
from tools.edid_tool import verify_edid_nvm


class TestStageUSB(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_stage_canary(self):
        stage_drive(
            target_dir=self.temp_dir,
            mode="canary",
            custom_vars=[],
            include_channels=False,
        )

        staged_uboot = os.path.join(self.temp_dir, "SAM", "nvm_ubootdat.data")
        self.assertTrue(os.path.exists(staged_uboot))

        nvm = UBootNVM.from_file(staged_uboot)
        i_ok, o_ok, _, _, _, _ = nvm.verify()
        self.assertTrue(i_ok)
        self.assertTrue(o_ok)
        self.assertEqual(nvm.variables.get("canary_test"), "1")

        staged_edid = os.path.join(self.temp_dir, "SAM", "nvm_edid.data")
        self.assertTrue(os.path.exists(staged_edid))
        with open(staged_edid, "rb") as f:
            e_ok, _, _ = verify_edid_nvm(f.read())
        self.assertTrue(e_ok)

    def test_stage_debug_cookie(self):
        stage_drive(
            target_dir=self.temp_dir,
            mode="canary",
            custom_vars=[],
            include_channels=False,
            debug_cookie=True,
        )
        cookie = os.path.join(self.temp_dir, "TPVisionDebug.cookie")
        log2usb = os.path.join(self.temp_dir, "enable_log2usb")
        self.assertTrue(os.path.exists(cookie))
        self.assertTrue(os.path.exists(log2usb))

    def test_stage_diag(self):
        stage_drive(
            target_dir=self.temp_dir,
            mode="diag",
            custom_vars=[],
            include_channels=False,
        )
        staged_uboot = os.path.join(self.temp_dir, "SAM", "nvm_ubootdat.data")
        self.assertTrue(os.path.exists(staged_uboot))

        nvm = UBootNVM.from_file(staged_uboot)
        i_ok, o_ok, _, _, _, _ = nvm.verify()
        self.assertTrue(i_ok)
        self.assertTrue(o_ok)
        self.assertEqual(nvm.variables.get("mds_mode"), "1")
        self.assertEqual(nvm.variables.get("watch_dog_timeout"), "0")
        self.assertEqual(nvm.variables.get("telnet_enable"), "1")
        self.assertEqual(nvm.variables.get("server_env"), "dev")


if __name__ == "__main__":
    unittest.main()
