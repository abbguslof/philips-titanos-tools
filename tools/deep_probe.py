#!/usr/bin/env python3
"""Read-only deep inventory for a rooted Philips Titan OS TV.

The probe never writes to the TV. It runs a fixed list of read-only commands
over SSH, stores the raw output under an ignored directory, and writes a
redacted Markdown report plus a manifest with per-command hashes.

Use the 55PUS8000/12 as the lab unit. For the 55PUS8450/12 or another owner's
TV, run only this read-only probe (and only with the owner's agreement). Do not
use the bootchain dumper or any write path on a unit you do not own.

Examples:
  python3 tools/deep_probe.py --host <TV_IP>
  python3 tools/deep_probe.py --host <TV_IP> --out dist/deep-probe/8000
  python3 tools/deep_probe.py --host <TV_IP> --hash-large-partitions

The raw directory can contain real device data. It defaults to `dist/`, which
is gitignored. Review the redacted report before copying anything into
`evidence/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=6",
    "-o", "StrictHostKeyChecking=accept-new",
]

# name, command, timeout seconds
COMMANDS = [
    ("identity", "id", 20),
    ("uname", "uname -a", 20),
    ("kernel-version", "cat /proc/version", 20),
    ("cmdline", "cat /proc/cmdline", 20),
    ("uptime", "cat /proc/uptime", 20),
    ("loadavg", "cat /proc/loadavg", 20),
    ("hostname", "cat /proc/sys/kernel/hostname", 20),
    ("device-tree-model", "cat /proc/device-tree/model 2>/dev/null", 20),
    ("device-tree-compatible", "cat /proc/device-tree/compatible 2>/dev/null", 20),
    ("partitions", "cat /proc/partitions", 20),
    ("mounts", "cat /proc/mounts", 20),
    ("filesystems", "cat /proc/filesystems", 20),
    ("block-sizes", "for n in 1 2 9 11 19 20 31 36; do printf 'mmcblk0p%s ' \"$n\"; cat /sys/class/block/mmcblk0p$n/size 2>/dev/null || echo unknown; done", 20),
    ("boot-area-flags", "for d in mmcblk0boot0 mmcblk0boot1; do echo \"$d\"; cat /sys/class/block/$d/size /sys/class/block/$d/force_ro /sys/class/block/$d/ro 2>/dev/null; done", 20),
    ("modules", "cat /proc/modules", 20),
    ("modules-disabled", "cat /proc/sys/kernel/modules_disabled", 20),
    ("kptr-restrict", "cat /proc/sys/kernel/kptr_restrict", 20),
    ("dmesg-restrict", "cat /proc/sys/kernel/dmesg_restrict", 20),
    ("iomem", "cat /proc/iomem", 20),
    ("module-files", "ls -l /mtd_apexe/board/modules 2>/dev/null", 20),
    ("module-hashes", "sha256sum /mtd_apexe/board/modules/*.ko 2>/dev/null", 120),
    ("selinux", "getenforce; cat /sys/fs/selinux/enforce 2>/dev/null; cat /sys/fs/selinux/policyvers 2>/dev/null; sha256sum /sys/fs/selinux/policy 2>/dev/null", 30),
    ("hooks", "grep -nE 'customer_env|/swdl/telnet/telnetd' /mtd_apexe/board/run.sh /mtd_apexe/board/run_custom_impl.sh 2>/dev/null", 20),
    ("apdat", "ls -l /mtd_rwarea/apdat 2>/dev/null", 20),
    ("swdl", "ls -l /swdl 2>/dev/null", 20),
    ("listeners", "netstat -ltn 2>/dev/null", 20),
    ("processes", "ps w 2>/dev/null || ps 2>/dev/null", 20),
    ("devices", "ls -l /dev/ntk* /dev/ndp* /dev/tee* /dev/uinput /dev/uhid /dev/mmcblk0boot* /dev/i2c-* /dev/fb* 2>/dev/null", 20),
    ("input-devices", "cat /proc/bus/input/devices 2>/dev/null", 20),
    ("sys-class", "ls /sys/class 2>/dev/null", 20),
    ("thermal", "for z in /sys/class/thermal/thermal_zone*; do [ -e \"$z\" ] || continue; printf '%s ' \"$z\"; cat \"$z/type\" 2>/dev/null; cat \"$z/temp\" 2>/dev/null; done", 20),
    ("graphics", "ls /sys/class/graphics /sys/class/backlight /sys/class/leds 2>/dev/null", 20),
    ("dmesg", "dmesg 2>/dev/null | tail -200", 30),
    ("boot0-hash", "sha256sum /dev/mmcblk0boot0 /dev/mmcblk0boot1 2>/dev/null", 120),
    ("small-partition-hashes", "sha256sum /dev/mmcblk0p9 /dev/mmcblk0p11 /dev/mmcblk0p36 2>/dev/null", 120),
]

LARGE_HASHES = [
    ("vendor-boot-hashes", "sha256sum /dev/mmcblk0p1 /dev/mmcblk0p2 2>/dev/null", 180),
    ("nfsb-root-hashes", "sha256sum /dev/mmcblk0p19 /dev/mmcblk0p20 2>/dev/null", 180),
]

IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
MAC = re.compile(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b")
IPV6 = re.compile(
    r"(?i)\b(?:(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}|"
    r"(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{0,4}::(?:[0-9a-f]{1,4}:){0,6}[0-9a-f]{0,4})\b"
)
SECRET = re.compile(
    r"(?i)\b(token|passwd|password|secret|authorization|auth_key|device[_-]?token|productinstanceid|serial(?:number|no)?|ssid)\b([=:]\s*)[^\s,;]+"
)


def redact(text: str) -> str:
    def mac(match: re.Match[str]) -> str:
        value = match.group(0)
        return value if value.lower() == "02:00:00:00:00:00" else "<MAC>"

    def ipv4(match: re.Match[str]) -> str:
        value = match.group(0)
        if value in ("127.0.0.1", "0.0.0.0") or value.startswith("192.0.2."):
            return value
        return "<IP>"

    def ipv6(match: re.Match[str]) -> str:
        value = match.group(0)
        return value if value in ("::1", "::") else "<IPV6>"

    # Keep the documentation MAC intact through the IPv6 pass.
    placeholder = "\x00DOC_MAC\x00"
    text = text.replace("02:00:00:00:00:00", placeholder)
    text = MAC.sub(mac, text)
    text = IPV4.sub(ipv4, text)
    text = IPV6.sub(ipv6, text)
    text = text.replace(placeholder, "02:00:00:00:00:00")
    return SECRET.sub(r"\1\2<REDACTED>", text)


def slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", name).strip("-") or "output"


def run_ssh(host: str, port: int, user: str, command: str, timeout: float) -> tuple[int, bytes, str]:
    ssh = ["ssh", "-p", str(port), *SSH_OPTS, f"{user}@{host}", command]
    try:
        result = subprocess.run(
            ssh,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or b""
        err = (exc.stderr or b"").decode("utf-8", "replace")
        return 124, out, err + f"\n[timeout after {timeout}s]"
    except FileNotFoundError:
        raise SystemExit("ssh not found on PATH")
    return result.returncode, result.stdout, result.stderr.decode("utf-8", "replace")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="TV address")
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--user", default="root")
    parser.add_argument("--out", default="", help="output directory (default dist/deep-probe/<host>-<utc>)")
    parser.add_argument("--timeout-scale", type=float, default=1.0)
    parser.add_argument(
        "--hash-large-partitions",
        action="store_true",
        help="also hash vendor boot p1/p2 and NFSB p19/p20 (about 108 MB of reads)",
    )
    args = parser.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out) if args.out else Path("dist") / "deep-probe" / stamp
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    commands = list(COMMANDS)
    if args.hash_large_partitions:
        commands.extend(LARGE_HASHES)

    manifest = {
        "tool": "deep_probe",
        "host": "<TV_IP>",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "commands": [],
    }
    sections = []
    failures = []

    for name, command, timeout in commands:
        print(f"[deep_probe] {name}", flush=True)
        rc, stdout, stderr = run_ssh(
            args.host,
            args.ssh_port,
            args.user,
            command,
            timeout * args.timeout_scale,
        )
        raw = stdout + stderr.encode("utf-8", "replace")
        raw_path = raw_dir / f"{slug(name)}.txt"
        raw_path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        if rc != 0:
            failures.append({"name": name, "rc": rc})
        manifest["commands"].append(
            {
                "name": name,
                "command": command,
                "returncode": rc,
                "timeout_seconds": timeout,
                "raw_file": str(raw_path.relative_to(out)),
                "bytes": len(raw),
                "sha256": digest,
            }
        )
        sections.append((name, command, rc, redact(raw.decode("utf-8", "replace"))))

    report = [
        "# Deep probe report",
        "",
        f"- Generated: `{manifest['started_at']}`",
        "- Target: `<TV_IP>`",
        "- Mode: **read-only** (no writes, no module loads, no ioctls)",
        "- Raw output: `raw/` beside this report (not for publication)",
        f"- Commands: {len(manifest['commands'])}",
        f"- Failures: {len(failures)}",
        "",
    ]
    if failures:
        report += ["## Failed commands", ""]
        for item in failures:
            report.append(f"- `{item['name']}` returned {item['rc']}")
        report.append("")
    for name, command, rc, body in sections:
        report += [f"## {name}", "", f"```sh\n{command}\n```", "", f"return code: `{rc}`", "", "```text", body.rstrip(), "```", ""]

    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"report:  {out / 'report.md'}")
    print(f"raw:     {raw_dir}")
    print(f"manifest:{out / 'manifest.json'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
