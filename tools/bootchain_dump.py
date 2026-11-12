#!/usr/bin/env python3
"""Read-only pull of the boot-chain and small metadata partitions.

This reads from the TV over SSH and writes only on the workstation. It never
writes, mounts, insmods, or flashes anything on the TV.

Use this on the owned 55PUS8000/12 lab unit. Do not use it on another owner's
TV without explicit consent, and never publish the raw outputs: the vendor boot
partitions and metadata may contain device identifiers.

Examples:
  python3 tools/bootchain_dump.py --host <TV_IP>
  python3 tools/bootchain_dump.py --host <TV_IP> --only boot0 boot1 p1 p2
  python3 tools/bootchain_dump.py --host <TV_IP> --full-nfsb
  python3 tools/bootchain_dump.py --host <TV_IP> --dry-run

The default output is `dist/bootchain/<utc>` (gitignored). The manifest records
sizes and SHA-256 hashes and is safe to review before publishing a summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=6",
    "-o", "StrictHostKeyChecking=accept-new",
]

MB = 1024 * 1024
KB = 1024

# name, source, offset, length, timeout seconds
ITEMS = [
    ("boot0", "/dev/mmcblk0boot0", 0, 4 * MB, 120),
    ("boot1", "/dev/mmcblk0boot1", 0, 4 * MB, 120),
    ("p1-vendor-boot0", "/dev/mmcblk0p1", 0, 24 * MB, 180),
    ("p2-vendor-boot1", "/dev/mmcblk0p2", 0, 24 * MB, 180),
    ("p3-ddr", "/dev/mmcblk0p3", 0, 64 * KB, 60),
    ("p4-ddr", "/dev/mmcblk0p4", 0, 64 * KB, 60),
    ("p7-pidx", "/dev/mmcblk0p7", 0, 64 * KB, 60),
    ("p8-pidx", "/dev/mmcblk0p8", 0, 64 * KB, 60),
    ("p9-misc", "/dev/mmcblk0p9", 0, 8 * MB, 120),
    ("p11-nvm", "/dev/mmcblk0p11", 0, 1 * MB, 60),
    ("p13-uboot", "/dev/mmcblk0p13", 0, 64 * KB, 60),
    ("p14-uboot", "/dev/mmcblk0p14", 0, 64 * KB, 60),
    ("p15-uboot", "/dev/mmcblk0p15", 0, 64 * KB, 60),
    ("p16-uboot", "/dev/mmcblk0p16", 0, 64 * KB, 60),
    ("p17-uboot", "/dev/mmcblk0p17", 0, 64 * KB, 60),
    ("p18-uboot", "/dev/mmcblk0p18", 0, 64 * KB, 60),
    ("p19-nfsb-header", "/dev/mmcblk0p19", 0, 4096, 30),
    ("p20-nfsb-header", "/dev/mmcblk0p20", 0, 4096, 30),
    ("p21-uboot", "/dev/mmcblk0p21", 0, 64 * KB, 60),
    ("p32-nfsb-header", "/dev/mmcblk0p32", 0, 4096, 30),
    ("p33-nfsb-header", "/dev/mmcblk0p33", 0, 4096, 30),
    ("p34-nfsb-header", "/dev/mmcblk0p34", 0, 4096, 30),
    ("p35-nfsb-header", "/dev/mmcblk0p35", 0, 4096, 30),
    ("p36-pstore", "/dev/mmcblk0p36", 0, 2 * MB, 60),
]

FULL_NFSB = [
    ("p19-nfsb-full", "/dev/mmcblk0p19", 0, 30 * MB, 240),
    ("p20-nfsb-full", "/dev/mmcblk0p20", 0, 30 * MB, 240),
]

FULL_BOOT = [
    ("p13-atf-full", "/dev/mmcblk0p13", 0, 8 * MB, 240),
    ("p14-atf-full", "/dev/mmcblk0p14", 0, 8 * MB, 240),
    ("p15-fdt-full", "/dev/mmcblk0p15", 0, 3 * MB, 120),
    ("p16-fdt-full", "/dev/mmcblk0p16", 0, 3 * MB, 120),
    ("p17-kernel-full", "/dev/mmcblk0p17", 0, 35 * MB, 300),
    ("p18-kernel-full", "/dev/mmcblk0p18", 0, 35 * MB, 300),
    ("p21-kernel-full", "/dev/mmcblk0p21", 0, 24 * MB, 300),
]

FULL_BOOT_HEADER_NAMES = {
    "p13-uboot", "p14-uboot", "p15-uboot", "p16-uboot",
    "p17-uboot", "p18-uboot", "p21-uboot",
}

APDAT_SLICE = [
    ("p31-apdat-slice", "/dev/mmcblk0p31", 0, 1 * MB, 60),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dd_command(source: str, offset: int, length: int) -> str:
    block = 4096
    if offset % block or length % block:
        raise ValueError(f"unaligned item: {source} offset={offset} length={length}")
    return (
        f"dd if={source} bs={block} skip={offset // block} count={length // block} 2>/dev/null"
    )


def run_item(host: str, port: int, user: str, item, out: Path, timeout: float):
    name, source, offset, length, item_timeout = item
    command = dd_command(source, offset, length)
    path = out / f"{name}.bin"
    ssh = ["ssh", "-p", str(port), *SSH_OPTS, f"{user}@{host}", command]
    with path.open("wb") as handle:
        try:
            result = subprocess.run(
                ssh,
                stdout=handle,
                stderr=subprocess.PIPE,
                timeout=item_timeout * timeout,
            )
            rc = result.returncode
            stderr = result.stderr.decode("utf-8", "replace")
        except subprocess.TimeoutExpired as exc:
            rc = 124
            stderr = str(exc)
    size = path.stat().st_size
    return {
        "name": name,
        "source": source,
        "offset": offset,
        "requested_bytes": length,
        "bytes": size,
        "sha256": sha256_file(path),
        "command": command,
        "returncode": rc,
        "stderr": stderr.strip()[-2000:],
        "complete": size == length and rc == 0,
        "file": path.name,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--user", default="root")
    parser.add_argument("--out", default="", help="output directory (default dist/bootchain/<utc>)")
    parser.add_argument("--only", nargs="+", default=[], help="only these item names")
    parser.add_argument("--full-nfsb", action="store_true", help="also pull p19/p20 full images")
    parser.add_argument("--full-boot", action="store_true", help="pull the full ATF/FDT/kernel partitions instead of headers")
    parser.add_argument("--include-apdat", action="store_true", help="pull a 1 MiB p31 slice")
    parser.add_argument("--timeout-scale", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    items = list(ITEMS)
    if args.full_boot:
        items = [item for item in items if item[0] not in FULL_BOOT_HEADER_NAMES]
        items.extend(FULL_BOOT)
    if args.full_nfsb:
        items.extend(FULL_NFSB)
    if args.include_apdat:
        items.extend(APDAT_SLICE)
    if args.only:
        wanted = set(args.only)
        items = [item for item in items if item[0] in wanted]
        missing = wanted - {item[0] for item in items}
        if missing:
            print(f"unknown item(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
    if not items:
        print("no items selected", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out) if args.out else Path("dist") / "bootchain" / stamp

    if args.dry_run:
        print(f"host: <TV_IP>  output: {out}")
        for name, source, offset, length, timeout in items:
            print(f"{name:20} {source:16} offset={offset:<10} bytes={length:<10} timeout={timeout}")
        print(f"total bytes: {sum(item[3] for item in items)}")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "tool": "bootchain_dump",
        "target": "<TV_IP>",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "items": [],
    }
    failures = []
    for item in items:
        print(f"[bootchain] {item[0]} ({item[3]} bytes)", flush=True)
        record = run_item(args.host, args.ssh_port, args.user, item, out, args.timeout_scale)
        manifest["items"].append(record)
        if not record["complete"]:
            failures.append(record["name"])
        print(f"  {record['bytes']} bytes  {record['sha256']}  {'ok' if record['complete'] else 'INCOMPLETE'}")

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "README.txt").write_text(
        "Boot-chain dump\n"
        "===============\n\n"
        "READ-ONLY COLLECTION FROM THE TV. This directory may contain vendor boot\n"
        "partitions and device identifiers. Keep it out of git and out of public\n"
        "evidence. The manifest hashes are safe to review; the .bin files are not.\n\n"
        "The TV was not written to. These are sequential dd reads over SSH.\n",
        encoding="utf-8",
    )
    print(f"manifest: {out / 'manifest.json'}")
    if failures:
        print(f"incomplete: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
