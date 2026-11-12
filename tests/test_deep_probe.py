#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import deep_probe  # noqa: E402


class TestDeepProbe(unittest.TestCase):
    def test_redaction(self):
        text = (
            "addr 198.51.100.23 and 127.0.0.1 and 192.0.2.10\n"
            "mac aa:bb:cc:dd:ee:ff and 02:00:00:00:00:00\n"
            "ipv6 fe80::1 and ::1\n"
            "token=abc123 serial: XYZ ssid=HomeNet\n"
        )
        redacted = deep_probe.redact(text)
        self.assertIn("<IP>", redacted)
        self.assertIn("127.0.0.1", redacted)
        self.assertIn("192.0.2.10", redacted)
        self.assertIn("<MAC>", redacted)
        self.assertIn("02:00:00:00:00:00", redacted)
        self.assertIn("<IPV6>", redacted)
        self.assertIn("::1", redacted)
        self.assertIn("token=<REDACTED>", redacted)
        self.assertIn("serial: <REDACTED>", redacted)
        self.assertIn("ssid=<REDACTED>", redacted)
        self.assertNotIn("198.51.100.23", redacted)
        self.assertNotIn("aa:bb:cc:dd:ee:ff", redacted)
        self.assertNotIn("abc123", redacted)

    def test_commands_are_read_only(self):
        forbidden = (
            " of=", ">>", " > ", "insmod", "rmmod", "mount ", "umount",
            "reboot", "rm -", "mv ", "cp ", "chmod", "tee ", "dd ",
            "mkfs", "wipefs", "sfdisk", "ioctl",
        )
        for name, command, _timeout in deep_probe.COMMANDS + deep_probe.LARGE_HASHES:
            for token in forbidden:
                self.assertNotIn(token, command, f"{name}: {token!r} in {command!r}")

    def test_command_names_are_unique(self):
        names = [item[0] for item in deep_probe.COMMANDS + deep_probe.LARGE_HASHES]
        self.assertEqual(len(names), len(set(names)))

    def test_slug_is_safe(self):
        self.assertEqual(deep_probe.slug("a/b c"), "a-b-c")
        self.assertEqual(deep_probe.slug(""), "output")


if __name__ == "__main__":
    unittest.main()
