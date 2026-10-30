#!/usr/bin/env python3
import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.autoroot_usb import (
    AUTOSCRIPT_LINE,
    AUTOSCRIPT_NAME,
    AUTOROOT_SH,
    BUSYBOX,
    EXPECTED_BUSYBOX_SHA256,
    MANIFEST_NAME,
    README_NAME,
    sha256_file,
    stage_files,
    validate_payload,
)


class TestAutorootUSB(unittest.TestCase):
    def test_payload_validation(self):
        hashes = validate_payload()
        self.assertEqual(hashes["busybox_sha256"], EXPECTED_BUSYBOX_SHA256)
        self.assertEqual(sha256_file(BUSYBOX), EXPECTED_BUSYBOX_SHA256)
        self.assertGreater(AUTOROOT_SH.stat().st_size, 0)
        self.assertIn(b"telnetd", BUSYBOX.read_bytes())

    def test_autoscript_is_one_safe_eval_line(self):
        self.assertEqual(AUTOSCRIPT_LINE.count("\n"), 1)
        self.assertTrue(AUTOSCRIPT_LINE.endswith("\n"))
        self.assertTrue(AUTOSCRIPT_LINE.startswith("/bin/sh /media/sda1/autoroot.sh"))
        self.assertNotIn("#", AUTOSCRIPT_LINE)
        first = AUTOSCRIPT_LINE.split(None, 1)[0]
        self.assertNotIn(first, {"sleep", "id", "kid", "r", "OVERNIGHT"})

    def test_stage_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            manifest = stage_files(target)

            self.assertTrue((target / AUTOSCRIPT_NAME).is_file())
            self.assertTrue((target / "autoroot.sh").is_file())
            self.assertTrue((target / "busybox-armhf").is_file())
            self.assertTrue((target / MANIFEST_NAME).is_file())
            self.assertTrue((target / README_NAME).is_file())

            self.assertEqual(
                (target / AUTOSCRIPT_NAME).read_bytes(),
                AUTOSCRIPT_LINE.encode("utf-8"),
            )
            self.assertEqual(sha256_file(target / "busybox-armhf"), EXPECTED_BUSYBOX_SHA256)
            self.assertEqual(manifest["busybox-armhf"], EXPECTED_BUSYBOX_SHA256)

            manifest_text = (target / MANIFEST_NAME).read_text(encoding="utf-8")
            for name, digest in manifest.items():
                self.assertIn(f"{digest}  {name}", manifest_text)

    def test_stage_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            first = stage_files(target)
            second = stage_files(target)
            self.assertEqual(first, second)
            self.assertEqual(
                (target / AUTOSCRIPT_NAME).read_text(encoding="utf-8"),
                AUTOSCRIPT_LINE,
            )

    def test_payload_contains_required_steps(self):
        script = AUTOROOT_SH.read_text(encoding="utf-8")
        for token in (
            "/media/sda1",
            "busybox-armhf",
            "/tmp/busybox",
            "telnetd -p",
            "/usr/sbin/iptables",
            "/usr/sbin/ip6tables",
            "-w 5",
            "/bin/netstat",
            "READY",
            "FAILED",
        ):
            self.assertIn(token, script)
        self.assertNotRegex(script, r"(?m)^\s*(/bin/|/usr/bin/)?pkill\b")


if __name__ == "__main__":
    unittest.main()
