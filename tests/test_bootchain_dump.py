#!/usr/bin/env python3
import contextlib
import io
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import bootchain_dump  # noqa: E402


class TestBootchainDump(unittest.TestCase):
    def test_items_are_aligned_and_unique(self):
        names = set()
        for name, _source, offset, length, _timeout in (
            bootchain_dump.ITEMS
            + bootchain_dump.FULL_NFSB
            + bootchain_dump.FULL_BOOT
            + bootchain_dump.APDAT_SLICE
        ):
            self.assertNotIn(name, names)
            names.add(name)
            self.assertEqual(offset % 4096, 0, name)
            self.assertEqual(length % 4096, 0, name)
            self.assertGreater(length, 0, name)

    def test_dd_is_read_only(self):
        command = bootchain_dump.dd_command("/dev/mmcblk0boot0", 0, 4 * 1024 * 1024)
        self.assertIn("if=/dev/mmcblk0boot0", command)
        self.assertNotIn("of=", command)
        self.assertIn("2>/dev/null", command)
        self.assertEqual(bootchain_dump.dd_command("/dev/x", 0, 4096),
                         "dd if=/dev/x bs=4096 skip=0 count=1 2>/dev/null")

    def test_dd_rejects_unaligned(self):
        with self.assertRaises(ValueError):
            bootchain_dump.dd_command("/dev/x", 1, 4096)
        with self.assertRaises(ValueError):
            bootchain_dump.dd_command("/dev/x", 0, 4097)

    def test_dry_run_does_not_connect(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = bootchain_dump.main(
                [
                    "--host", "192.0.2.10",
                    "--dry-run",
                    "--only", "boot0", "p1-vendor-boot0",
                ]
            )
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn("boot0", text)
        self.assertIn("p1-vendor-boot0", text)
        self.assertIn("<TV_IP>", text)
        self.assertNotIn("192.0.2.10", text)

    def test_full_boot_dry_run_replaces_headers(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = bootchain_dump.main(
                [
                    "--host", "192.0.2.10",
                    "--dry-run",
                    "--full-boot",
                    "--only", "p13-atf-full", "p17-kernel-full",
                ]
            )
        self.assertEqual(code, 0)
        text = stdout.getvalue()
        self.assertIn("p13-atf-full", text)
        self.assertIn("p17-kernel-full", text)
        self.assertNotIn("p13-uboot", text)

    def test_default_items_include_boot_areas_and_headers(self):
        names = {item[0] for item in bootchain_dump.ITEMS}
        self.assertIn("boot0", names)
        self.assertIn("boot1", names)
        self.assertIn("p1-vendor-boot0", names)
        self.assertIn("p20-nfsb-header", names)
        self.assertIn("p36-pstore", names)
        self.assertNotIn("p31-apdat-slice", names)


if __name__ == "__main__":
    unittest.main()
