#!/usr/bin/env python3
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER = REPO_ROOT / "payloads" / "persist_root.sh"


def embedded_root_boot() -> str:
    text = INSTALLER.read_text(encoding="utf-8")
    marker = "<<'ROOTBOOT'\n"
    start = text.index(marker) + len(marker)
    end = text.index("\nROOTBOOT\n", start)
    return text[start:end] + "\n"


class TestPersistRoot(unittest.TestCase):
    def setUp(self):
        self.installer = INSTALLER.read_text(encoding="utf-8")
        self.root_boot = embedded_root_boot()

    def test_installer_targets_customer_env_hook(self):
        self.assertIn("/mtd_rwarea/apdat", self.installer)
        self.assertIn("customer_env.sh", self.installer)
        self.assertIn("root_boot.sh", self.installer)
        self.assertIn("/tmp/busybox", self.installer)
        self.assertIn(
            "printf '\\n[ -f /mtd_rwarea/apdat/root_boot.sh ] && "
            "/bin/sh /mtd_rwarea/apdat/root_boot.sh &\\n'",
            self.installer,
        )

    def test_root_boot_script_syntax(self):
        result = subprocess.run(
            ["sh", "-n"], input=self.root_boot, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_root_boot_is_network_only_and_delayed(self):
        self.assertIn("/tmp/persist/busybox", self.root_boot)
        self.assertNotIn("/media/sda1", self.root_boot)
        self.assertIn("/tmp/ntkdriver_completed", self.root_boot)
        self.assertIn("sleep 5", self.root_boot)
        self.assertIn("iptables -w 5", self.root_boot)
        self.assertIn("telnetd -p", self.root_boot)
        self.assertIn("root_boot.ready", self.root_boot)
        self.assertNotRegex(self.root_boot, r"(?m)^\s*(/bin/|/usr/bin/)?pkill\b")
        self.assertNotIn("iptables -F", self.root_boot)


if __name__ == "__main__":
    unittest.main()
