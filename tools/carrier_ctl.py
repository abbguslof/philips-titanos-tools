#!/usr/bin/env python3
"""Drive the reusable ndp_logo kernel carrier over SSH (Level 3.5).

The carrier module (built by tools/build_carrier.py) exposes
`/sys/module/ndp_logo/parameters/carrier`. This tool resolves symbols from
`/proc/kallsyms`, reads and writes 64-bit kernel words, calls kernel functions,
and performs a `copy_from_kernel_nofault`-backed read.

This is a lab primitive. A bad address can fault the kernel and require a cold
boot. Writes and calls require `--yes`. The tool never writes the boot chain,
the eMMC, or any partition.

Examples:
  python3 tools/carrier_ctl.py --host <TV_IP> status
  python3 tools/carrier_ctl.py --host <TV_IP> probe
  python3 tools/carrier_ctl.py --host <TV_IP> selftest
  python3 tools/carrier_ctl.py --host <TV_IP> sym selinux_state nfsb_verify
  python3 tools/carrier_ctl.py --host <TV_IP> scratch
  python3 tools/carrier_ctl.py --host <TV_IP> dump nfsb_verify --length 64
  python3 tools/carrier_ctl.py --host <TV_IP> read selinux_state
  python3 tools/carrier_ctl.py --host <TV_IP> safe-read selinux_state
  python3 tools/carrier_ctl.py --host <TV_IP> --yes write selinux_state 0x1
  python3 tools/carrier_ctl.py --host <TV_IP> --yes call copy_from_kernel_nofault 0x...
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=6",
    "-o", "StrictHostKeyChecking=accept-new",
]
DEFAULT_MODULE = "ndp_logo"
DEFAULT_PARAM = "carrier"
MAGIC = 0x0D15EA5E0D15EA5E
SELFTEST_MARKER = 0xCAFEBABEDEADBEEF
SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.$]*$")
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
HEX_RE = re.compile(r"^0[xX][0-9a-fA-F]{1,16}$")
WORD_RE = re.compile(r"0x[0-9a-fA-F]{16}")


class CtlError(Exception):
    """A carrier control or validation failure."""


def param_path(module: str, param: str) -> str:
    if not NAME_RE.match(module) or not NAME_RE.match(param):
        raise CtlError(f"invalid module/param name: {module!r}/{param!r}")
    return f"/sys/module/{module}/parameters/{param}"


def validate_symbol(name: str) -> str:
    if not SYMBOL_RE.match(name):
        raise CtlError(f"invalid symbol name: {name!r}")
    return name


def parse_hex(text: str) -> int:
    if not HEX_RE.match(text):
        raise CtlError(f"address must be 0x-prefixed hex: {text!r}")
    return int(text, 16)


def parse_value(text: str) -> int:
    try:
        return int(text, 0) & 0xFFFFFFFFFFFFFFFF
    except ValueError:
        raise CtlError(f"invalid value: {text!r}")


def format_word(value: int) -> str:
    return f"0x{value & 0xFFFFFFFFFFFFFFFF:016x}"


def is_kernel_address(addr: int) -> bool:
    return (addr >> 48) == 0xFFFF


def symbol_assign(var: str, name: str) -> str:
    validate_symbol(name)
    return (
        f"{var}=$(awk -v n={shlex.quote(name)} '$3==n{{print \"0x\"$1; exit}}' /proc/kallsyms); "
        f"[ -n \"${var}\" ] || {{ echo {shlex.quote(name + ' not found')} >&2; exit 3; }}"
    )


def target_assign(var: str, target: str, allow_any: bool = False) -> str:
    if target.lower().startswith("0x"):
        addr = parse_hex(target)
        if not allow_any and not is_kernel_address(addr):
            raise CtlError(f"refusing non-kernel address {target}; kernel VAs start with 0xffff")
        return f"{var}={format_word(addr)}"
    return symbol_assign(var, target)


def address_guard(var: str, allow_any: bool = False) -> str:
    if allow_any:
        return ""
    return (
        f"case \"${var}\" in 0xffff*) ;; "
        f"*) echo 'refusing non-kernel address' >&2; exit 4;; esac"
    )


def read_script(param: str, target: str, allow_any: bool = False) -> str:
    lines = [target_assign("addr", target, allow_any), address_guard("addr", allow_any)]
    lines.append(f"p={shlex.quote(param)}; printf '%s' \"r $addr\" > \"$p\" && cat \"$p\"")
    return "\n".join(line for line in lines if line)


def write_script(param: str, target: str, value: int, allow_any: bool = False) -> str:
    lines = [target_assign("addr", target, allow_any), address_guard("addr", allow_any)]
    lines.append(
        f"p={shlex.quote(param)}; printf '%s' \"w $addr {format_word(value)}\" > \"$p\" && cat \"$p\""
    )
    return "\n".join(line for line in lines if line)


def call_script(param: str, target: str, args: list[int], allow_any: bool = False) -> str:
    lines = [target_assign("addr", target, allow_any), address_guard("addr", allow_any)]
    arg_text = " ".join(format_word(arg) for arg in args)
    command = f"c $addr {arg_text}".rstrip()
    lines.append(f"p={shlex.quote(param)}; printf '%s' \"{command}\" > \"$p\" && cat \"$p\"")
    return "\n".join(line for line in lines if line)


def probe_script(param: str) -> str:
    return f"p={shlex.quote(param)}; printf '%s' n > \"$p\" && cat \"$p\""


def scratch_script(param: str) -> str:
    return f"p={shlex.quote(param)}; printf '%s' a > \"$p\" && cat \"$p\""


def poke_script(param: str, address: int, data: bytes) -> str:
    lines = [f"p={shlex.quote(param)}"]
    for offset in range(0, len(data), 8):
        word = int.from_bytes(data[offset:offset + 8].ljust(8, b"\0"), "little")
        lines.append(
            f"printf '%s' \"w {format_word(address + offset)} {format_word(word)}\" > \"$p\" "
            "|| { echo POKE_ERR; exit 6; }"
        )
    lines.append("echo POKE_OK")
    return "\n".join(lines)


def selftest_script(param: str, marker: int = SELFTEST_MARKER) -> str:
    return "\n".join(
        [
            f"p={shlex.quote(param)}",
            "printf '%s' n > \"$p\"; n=$(cat \"$p\")",
            "printf '%s' a > \"$p\"; b=$(cat \"$p\")",
            "case \"$b\" in 0xffff*) ;; "
            "*) echo \"BADBUF $b\" >&2; exit 5;; esac",
            f"printf '%s' \"w $b {format_word(marker)}\" > \"$p\"; w=$(cat \"$p\")",
            "printf '%s' m > \"$p\"; m=$(cat \"$p\")",
            "echo \"PROBE $n\"; echo \"BUF $b\"; echo \"WRITE $w\"; echo \"READ $m\"",
        ]
    )


def dump_script(param: str, addresses: list[int]) -> str:
    lines = [
        symbol_assign("fn", "copy_from_kernel_nofault"),
        f"p={shlex.quote(param)}",
        "printf '%s' a > \"$p\"; b=$(cat \"$p\")",
        "case \"$b\" in 0xffff*) ;; *) echo 'BADBUF' >&2; exit 5;; esac",
    ]
    for address in addresses:
        word = format_word(address)
        lines += [
            f"printf '%s' \"c $fn $b {word} 8\" > \"$p\"; r=$(cat \"$p\")",
            "if [ \"$r\" = \"0x0000000000000000\" ]; then "
            "printf '%s' m > \"$p\"; v=$(cat \"$p\"); else v=ERR; fi",
            f"echo \"{word} $r $v\"",
        ]
    return "\n".join(lines)


def safe_read_script(param: str, target: str, allow_any: bool = False) -> str:
    lines = [
        symbol_assign("fn", "copy_from_kernel_nofault"),
        target_assign("src", target, allow_any),
        address_guard("src", allow_any),
        f"p={shlex.quote(param)}",
        "printf '%s' a > \"$p\"; b=$(cat \"$p\")",
        "printf '%s' \"c $fn $b $src 8\" > \"$p\"; r=$(cat \"$p\")",
        "printf '%s' m > \"$p\"; v=$(cat \"$p\")",
        "echo \"BUF $b\"; echo \"RET $r\"; echo \"VAL $v\"",
    ]
    return "\n".join(line for line in lines if line)


def resolve_script(names: list[str]) -> str:
    return "\n".join(
        f"awk -v n={shlex.quote(validate_symbol(name))} "
        f"'$3==n{{print n\" 0x\"$1; exit}}' /proc/kallsyms"
        for name in names
    )


def status_script(param: str) -> str:
    return "\n".join(
        [
            "uname -r",
            "grep '^ndp_logo ' /proc/modules || echo 'ndp_logo: not loaded'",
            f"p={shlex.quote(param)}",
            "if [ -e \"$p\" ]; then ls -l \"$p\"; cat \"$p\"; "
            "else echo 'carrier parameter: missing'; fi",
            "cat /proc/sys/kernel/kptr_restrict",
        ]
    )


def run_ssh(host: str, port: int, user: str, script: str, timeout: float):
    cmd = ["ssh", "-p", str(port), *SSH_OPTS, f"{user}@{host}", script]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise CtlError("ssh timed out; the kernel may have faulted and need a cold boot")
    except FileNotFoundError:
        raise CtlError("ssh not found on PATH")


def resolve_one(args: argparse.Namespace, target: str) -> int:
    if target.lower().startswith("0x"):
        return parse_hex(target)
    validate_symbol(target)
    result = execute(args, resolve_script([target]))
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == target and WORD_RE.fullmatch(parts[1]):
            return int(parts[1], 16)
    raise CtlError(f"symbol {target} not found")


def parse_word_output(text: str) -> int:
    match = WORD_RE.search(text)
    if not match:
        raise CtlError(f"no 64-bit result in output: {text.strip()!r}")
    return int(match.group(0), 16)


def parse_labels(text: str) -> dict[str, int]:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and WORD_RE.fullmatch(parts[1]):
            out[parts[0]] = int(parts[1], 16)
    return out


def execute(args: argparse.Namespace, script: str) -> subprocess.CompletedProcess:
    if args.dry_run:
        print(script)
        raise SystemExit(0)
    result = run_ssh(args.host, args.port, args.user, script, args.timeout)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise CtlError(f"remote command failed ({result.returncode}): {detail}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--host", required=True, help="TV address")
    parser.add_argument("--port", type=int, default=2222, help="SSH port (default 2222)")
    parser.add_argument("--user", default="root", help="SSH user (default root)")
    parser.add_argument("--module-name", default=DEFAULT_MODULE)
    parser.add_argument("--param-name", default=DEFAULT_PARAM)
    parser.add_argument("--timeout", type=float, default=15.0, help="ssh timeout seconds")
    parser.add_argument("--dry-run", action="store_true", help="print the remote script only")
    parser.add_argument("--any-address", action="store_true", help="skip the kernel-VA guard")
    parser.add_argument("--yes", action="store_true", help="confirm a write or call")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show kernel, module and parameter state")
    sub.add_parser("probe", help="write the probe magic and read it back")
    sub.add_parser("selftest", help="probe, then write and read the carrier scratch word")
    sub.add_parser("scratch", help="print the carrier scratch buffer address")
    sym = sub.add_parser("sym", help="resolve symbols from /proc/kallsyms")
    sym.add_argument("names", nargs="+")
    read = sub.add_parser("read", help="read one 64-bit kernel word")
    read.add_argument("target")
    write = sub.add_parser("write", help="write one 64-bit kernel word")
    write.add_argument("target")
    write.add_argument("value")
    call = sub.add_parser("call", help="call a kernel address with up to six arguments")
    call.add_argument("target")
    call.add_argument("values", nargs="*")
    safer = sub.add_parser("safe-read", help="read through copy_from_kernel_nofault")
    safer.add_argument("target")
    dump = sub.add_parser("dump", help="hex dump through copy_from_kernel_nofault")
    dump.add_argument("target")
    dump.add_argument("--length", type=int, default=64)
    dump.add_argument("--offset", type=int, default=0)
    dump.add_argument("--raw", help="write the bytes to a local file")
    poke = sub.add_parser("poke", help="write local bytes to a kernel address")
    poke.add_argument("target")
    poke.add_argument("--from-file", required=True)
    poke.add_argument("--offset", type=int, default=0)
    poke.add_argument("--length", type=int, default=0)

    args = parser.parse_args(argv)
    try:
        param = param_path(args.module_name, args.param_name)
        if args.command in ("write", "call", "poke") and not args.yes:
            print("carrier_ctl: refusing write/call without --yes", file=sys.stderr)
            return 2

        if args.command == "status":
            result = execute(args, status_script(param))
            print(result.stdout.rstrip())
            return 0
        if args.command == "probe":
            value = parse_word_output(execute(args, probe_script(param)).stdout)
            if value != MAGIC:
                raise CtlError(f"unexpected probe result {format_word(value)}")
            print(f"carrier ok: {format_word(value)}")
            return 0
        if args.command == "scratch":
            value = parse_word_output(execute(args, scratch_script(param)).stdout)
            if not is_kernel_address(value) and not args.any_address:
                raise CtlError(f"scratch address is not a kernel VA: {format_word(value)}")
            print(format_word(value))
            return 0
        if args.command == "selftest":
            labels = parse_labels(execute(args, selftest_script(param)).stdout)
            if labels.get("PROBE") != MAGIC:
                raise CtlError(f"probe failed: {labels.get('PROBE')}")
            if not is_kernel_address(labels.get("BUF", 0)):
                raise CtlError(f"scratch address is not a kernel VA: {labels.get('BUF')}")
            if labels.get("WRITE") != 0:
                raise CtlError(f"scratch write failed: {labels.get('WRITE')}")
            if labels.get("READ") != SELFTEST_MARKER:
                raise CtlError(f"scratch read mismatch: {labels.get('READ')}")
            print(
                "carrier selftest ok: "
                f"probe={format_word(MAGIC)} "
                f"buf={format_word(labels['BUF'])} "
                f"read={format_word(SELFTEST_MARKER)}"
            )
            return 0
        if args.command == "sym":
            result = execute(args, resolve_script(args.names))
            found = set()
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) == 2 and WORD_RE.fullmatch(parts[1]):
                    found.add(parts[0])
                    print(f"{parts[0]} {parts[1]}")
            for name in args.names:
                if name not in found:
                    print(f"{name}: not found", file=sys.stderr)
            return 0
        if args.command == "read":
            value = parse_word_output(
                execute(args, read_script(param, args.target, args.any_address)).stdout
            )
            print(format_word(value))
            return 0
        if args.command == "write":
            value = parse_value(args.value)
            parse_word_output(
                execute(args, write_script(param, args.target, value, args.any_address)).stdout
            )
            print(f"wrote {format_word(value)} to {args.target}")
            return 0
        if args.command == "call":
            values = [parse_value(value) for value in args.values]
            result = parse_word_output(
                execute(args, call_script(param, args.target, values, args.any_address)).stdout
            )
            print(f"return {format_word(result)}")
            return 0
        if args.command == "dump":
            if args.length < 1 or args.length > 4096:
                raise CtlError("dump length must be 1..4096")
            base = resolve_one(args, args.target)
            if not is_kernel_address(base) and not args.any_address:
                raise CtlError(f"refusing non-kernel address {format_word(base)}")
            base += args.offset
            if not is_kernel_address(base) and not args.any_address:
                raise CtlError(f"refusing non-kernel address {format_word(base)}")
            count = (args.length + 7) // 8
            addresses = [base + 8 * i for i in range(count)]
            result = execute(args, dump_script(param, addresses))
            values = {}
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) != 3 or not WORD_RE.fullmatch(parts[0]):
                    continue
                address = int(parts[0], 16)
                if parts[1] == "0x0000000000000000" and WORD_RE.fullmatch(parts[2]):
                    values[address] = int(parts[2], 16)
            raw = bytearray()
            for address in addresses:
                if address not in values:
                    raise CtlError(f"dump failed at {format_word(address)}")
                raw += values[address].to_bytes(8, "little")
            raw = bytes(raw[:args.length])
            if args.raw:
                Path(args.raw).write_bytes(raw)
            for offset in range(0, len(raw), 16):
                chunk = raw[offset:offset + 16]
                print(f"{format_word(base + offset)}  " + " ".join(f"{b:02x}" for b in chunk))
            return 0
        if args.command == "poke":
            try:
                data = Path(args.from_file).read_bytes()
            except OSError as exc:
                raise CtlError(f"cannot read {args.from_file}: {exc}")
            if args.offset < 0 or args.offset > len(data):
                raise CtlError("poke offset out of range")
            end = len(data) if args.length <= 0 else args.offset + args.length
            data = data[args.offset:end]
            if not data:
                raise CtlError("poke data is empty")
            base = resolve_one(args, args.target)
            if not is_kernel_address(base) and not args.any_address:
                raise CtlError(f"refusing non-kernel address {format_word(base)}")
            result = execute(args, poke_script(param, base, data))
            if "POKE_OK" not in result.stdout:
                raise CtlError("poke failed")
            print(f"poked {len(data)} bytes to {format_word(base)}")
            return 0
        if args.command == "safe-read":
            result = execute(args, safe_read_script(param, args.target, args.any_address))
            labels = parse_labels(result.stdout)
            for name in ("BUF", "RET", "VAL"):
                if name not in labels:
                    raise CtlError(f"safe-read did not return {name}: {result.stdout.strip()!r}")
            if labels["RET"] != 0:
                raise CtlError(f"copy_from_kernel_nofault returned {format_word(labels['RET'])}")
            print(format_word(labels["VAL"]))
            return 0
        raise CtlError(f"unknown command {args.command!r}")
    except CtlError as exc:
        print(f"carrier_ctl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
