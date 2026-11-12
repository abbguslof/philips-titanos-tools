#!/usr/bin/env python3
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "payloads" / "emmc_backup.sh"


class TestEmmcBackup(unittest.TestCase):
    def test_shell_syntax(self):
        result = subprocess.run(["sh", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_read_only_and_safe_contract(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for token in (
            "if=/dev/mmcblk0",
            "if=/dev/mmcblk0boot0",
            "if=/dev/mmcblk0boot1",
            "sha256sum emmc-user.img",
            "/dev/sd*",
            "vfat|msdos",
            "cannot hold a >4 GiB image",
            "not a USB",
        ):
            self.assertIn(token, text)
        self.assertNotIn("of=/dev/", text)
        self.assertNotIn("mount -o rw", text)


if __name__ == "__main__":
    unittest.main()
