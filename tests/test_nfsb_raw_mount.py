#!/usr/bin/env python3
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "payloads" / "nfsb_raw_mount.sh"


class TestNfsbRawMount(unittest.TestCase):
    def test_shell_syntax(self):
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        result = subprocess.run(
            ["sh", "-n", str(SCRIPT)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_usage_without_arguments(self):
        result = subprocess.run(
            ["sh", str(SCRIPT)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", (result.stdout + result.stderr).lower())

    def test_contract(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for token in (
            "losetup -r",
            "mount -t squashfs -o ro",
            "dd if=\"$part\"",
            "offset",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
