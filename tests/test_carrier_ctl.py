#!/usr/bin/env python3
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
import carrier_ctl  # noqa: E402

KERNEL_ADDR = 0xFFFFFFC000000000


class FakeResult:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


class TestValidation(unittest.TestCase):
    def test_param_path(self):
        self.assertEqual(
            carrier_ctl.param_path("ndp_logo", "carrier"),
            "/sys/module/ndp_logo/parameters/carrier",
        )
        with self.assertRaises(carrier_ctl.CtlError):
            carrier_ctl.param_path("../x", "carrier")

    def test_symbol_validation(self):
        self.assertEqual(carrier_ctl.validate_symbol("selinux_state"), "selinux_state")
        self.assertEqual(carrier_ctl.validate_symbol("nfsb_verify"), "nfsb_verify")
        for bad in ("", "a b", "a;id", "$(x)", "a/b"):
            with self.assertRaises(carrier_ctl.CtlError):
                carrier_ctl.validate_symbol(bad)

    def test_address_helpers(self):
        self.assertTrue(carrier_ctl.is_kernel_address(KERNEL_ADDR))
        self.assertTrue(carrier_ctl.is_kernel_address(0xFFFFFFC0093CAAF0))
        self.assertFalse(carrier_ctl.is_kernel_address(0x1234))
        self.assertEqual(carrier_ctl.format_word(0x1), "0x0000000000000001")
        self.assertEqual(carrier_ctl.parse_hex("0x10"), 16)
        with self.assertRaises(carrier_ctl.CtlError):
            carrier_ctl.parse_hex("16")

    def test_value_parsing(self):
        self.assertEqual(carrier_ctl.parse_value("0x10"), 16)
        self.assertEqual(carrier_ctl.parse_value("16"), 16)
        with self.assertRaises(carrier_ctl.CtlError):
            carrier_ctl.parse_value("nope")

    def test_first_boot_guard_rejects_literal(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = carrier_ctl.main(["--host", "x", "read", "0x1234"])
        self.assertEqual(rc, 2)
        self.assertIn("non-kernel address", stderr.getvalue())


class TestScripts(unittest.TestCase):
    def setUp(self):
        self.param = carrier_ctl.param_path("ndp_logo", "carrier")

    def test_probe(self):
        script = carrier_ctl.probe_script(self.param)
        self.assertIn("printf '%s' n", script)
        self.assertIn("cat", script)

    def test_selftest(self):
        script = carrier_ctl.selftest_script(self.param)
        self.assertIn("BADBUF", script)
        self.assertIn("w $b 0xcafebabedeadbeef", script)
        self.assertIn("printf '%s' m", script)

    def test_read_symbol(self):
        script = carrier_ctl.read_script(self.param, "selinux_state")
        self.assertIn("awk -v n=selinux_state", script)
        self.assertIn('print "0x"$1', script)
        self.assertIn("0xffff*", script)
        self.assertIn('"r $addr"', script)

    def test_write_literal(self):
        script = carrier_ctl.write_script(self.param, "0xffffffc000000000", 0x1)
        self.assertIn("addr=0xffffffc000000000", script)
        self.assertIn('"w $addr 0x0000000000000001"', script)

    def test_call(self):
        script = carrier_ctl.call_script(self.param, "0xffffffc000000000", [1, 2, 3])
        self.assertIn('"c $addr 0x0000000000000001 0x0000000000000002 0x0000000000000003"', script)

    def test_dump(self):
        script = carrier_ctl.dump_script(self.param, [0xFFFFFFC000000000])
        self.assertIn("copy_from_kernel_nofault", script)
        self.assertIn("c $fn $b 0xffffffc000000000 8", script)
        self.assertIn("printf '%s' m", script)

    def test_scratch(self):
        script = carrier_ctl.scratch_script(self.param)
        self.assertIn("printf '%s' a", script)

    def test_poke(self):
        script = carrier_ctl.poke_script(
            self.param, 0xFFFFFFC000000000, bytes(range(16))
        )
        self.assertIn("w 0xffffffc000000000 0x0706050403020100", script)
        self.assertIn("w 0xffffffc000000008 0x0f0e0d0c0b0a0908", script)
        self.assertIn("POKE_OK", script)

    def test_safe_read(self):
        script = carrier_ctl.safe_read_script(self.param, "nfsb_verify")
        self.assertIn("copy_from_kernel_nofault", script)
        self.assertIn('printf \'%s\' a', script)
        self.assertIn('printf \'%s\' m', script)
        self.assertIn("RET", script)

    def test_resolve(self):
        script = carrier_ctl.resolve_script(["selinux_state", "nfsb_verify"])
        self.assertIn("n=selinux_state", script)
        self.assertIn("n=nfsb_verify", script)
        self.assertIn('print n" 0x"$1', script)


class TestFlows(unittest.TestCase):
    def setUp(self):
        self.original = carrier_ctl.run_ssh
        self.calls = []

    def tearDown(self):
        carrier_ctl.run_ssh = self.original

    def fake(self, stdout):
        def runner(host, port, user, script, timeout):
            self.calls.append(script)
            return FakeResult(stdout=stdout)

        carrier_ctl.run_ssh = runner

    def test_probe_flow(self):
        self.fake("0x0d15ea5e0d15ea5e\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(["--host", "x", "probe"])
        self.assertEqual(rc, 0)
        self.assertIn("carrier ok", out.getvalue())
        self.assertIn("printf '%s' n", self.calls[0])

    def test_selftest_flow(self):
        self.fake(
            "PROBE 0x0d15ea5e0d15ea5e\n"
            "BUF 0xffffffc001234000\n"
            "WRITE 0x0000000000000000\n"
            "READ 0xcafebabedeadbeef\n"
        )
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(["--host", "x", "selftest"])
        self.assertEqual(rc, 0)
        self.assertIn("carrier selftest ok", out.getvalue())

    def test_selftest_rejects_bad_read(self):
        self.fake(
            "PROBE 0x0d15ea5e0d15ea5e\n"
            "BUF 0xffffffc001234000\n"
            "WRITE 0x0000000000000000\n"
            "READ 0x0000000000000000\n"
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = carrier_ctl.main(["--host", "x", "selftest"])
        self.assertEqual(rc, 2)
        self.assertIn("scratch read mismatch", stderr.getvalue())

    def test_scratch_flow(self):
        self.fake("0xffffffc000000000\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(["--host", "x", "scratch"])
        self.assertEqual(rc, 0)
        self.assertIn("0xffffffc000000000", out.getvalue())

    def test_poke_requires_yes(self):
        self.fake("POKE_OK\n")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = carrier_ctl.main(
                ["--host", "x", "poke", "0xffffffc000000000", "--from-file", __file__]
            )
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls, [])
        self.assertIn("--yes", stderr.getvalue())

    def test_poke_flow(self):
        def runner(host, port, user, script, timeout):
            self.calls.append(script)
            if "POKE_OK" not in script:
                return FakeResult(stdout="carrier_buf 0xffffffc000000000\n")
            return FakeResult(stdout="POKE_OK\n")

        carrier_ctl.run_ssh = runner
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(
                [
                    "--host", "x", "--yes", "poke", "carrier_buf",
                    "--from-file", __file__, "--length", "16",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertIn("poked 16 bytes", out.getvalue())

    def test_read_flow(self):
        self.fake("0x0000000000000001\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(["--host", "x", "read", "0xffffffc000000000"])
        self.assertEqual(rc, 0)
        self.assertIn("0x0000000000000001", out.getvalue())

    def test_write_requires_yes(self):
        self.fake("0x0000000000000000\n")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = carrier_ctl.main(["--host", "x", "write", "0xffffffc000000000", "0x1"])
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls, [])
        self.assertIn("--yes", stderr.getvalue())

    def test_write_rejects_bad_value(self):
        self.fake("0x0000000000000000\n")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = carrier_ctl.main(
                ["--host", "x", "--yes", "write", "0xffffffc000000000", "nope"]
            )
        self.assertEqual(rc, 2)
        self.assertEqual(self.calls, [])

    def test_write_with_yes(self):
        self.fake("0x0000000000000000\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(
                ["--host", "x", "--yes", "write", "0xffffffc000000000", "0x1"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("wrote", out.getvalue())

    def test_dump_flow(self):
        def runner(host, port, user, script, timeout):
            self.calls.append(script)
            if "copy_from_kernel_nofault" not in script:
                return FakeResult(stdout="selinux_state 0xffffffc000000000\n")
            return FakeResult(
                stdout=(
                    "0xffffffc000000000 0x0000000000000000 0x0000000000000001\n"
                    "0xffffffc000000008 0x0000000000000000 0x0000000000000002\n"
                )
            )

        carrier_ctl.run_ssh = runner
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(
                ["--host", "x", "dump", "selinux_state", "--length", "16"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("01 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00", out.getvalue())

    def test_safe_read_flow(self):
        self.fake("BUF 0xffffffc000001000\nRET 0x0000000000000000\nVAL 0x0000000000001234\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = carrier_ctl.main(["--host", "x", "safe-read", "selinux_state"])
        self.assertEqual(rc, 0)
        self.assertIn("0x0000000000001234", out.getvalue())

    def test_safe_read_fault(self):
        self.fake("BUF 0xffffffc000001000\nRET 0xfffffffffffffff2\nVAL 0x0000000000000000\n")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rc = carrier_ctl.main(["--host", "x", "safe-read", "selinux_state"])
        self.assertEqual(rc, 2)
        self.assertIn("copy_from_kernel_nofault returned", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
