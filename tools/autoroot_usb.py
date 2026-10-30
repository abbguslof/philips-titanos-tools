#!/usr/bin/env python3
"""
Build the one-job Titan OS autoroot USB.

The TV executes /media/sda1/autoscript*.txt as root at boot via
/mtd_apexe/board/quick_debug/menu auto. This tool creates a USB stick that
does exactly that one job:

  autoscript.txt  -> one eval line that runs autoroot.sh
  autoroot.sh     -> starts busybox telnetd on :2323 and logs the result
  busybox-armhf   -> static armhf busybox with the telnetd applet

The stick MUST use an MBR partition table, one FAT32 partition, and an EMPTY
volume label. mdev mounts an unlabelled partition at /media/sda1; a labelled
partition lands at /media/<LABEL> and menu:19 never finds the autoscript.

Examples:
  sudo ./tools/autoroot_usb.py --device /dev/sdb
  sudo ./tools/autoroot_usb.py --device /dev/sdb --yes --host 192.0.2.10
  ./tools/autoroot_usb.py --stage /tmp/autoroot-usb     # test/stage only

After staging, cold boot the TV with the stick inserted. The menu sleeps 30
seconds before eval, so the port opens roughly 36 seconds after power-on.
"""

import argparse
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_DIR = REPO_ROOT / "payloads"
AUTOROOT_SH = PAYLOAD_DIR / "autoroot.sh"
BUSYBOX = PAYLOAD_DIR / "busybox-armhf"

AUTOSCRIPT_NAME = "autoscript.txt"
AUTOSCRIPT_LINE = "/bin/sh /media/sda1/autoroot.sh >>/media/sda1/autoroot.log 2>&1\n"
MANIFEST_NAME = "autoroot.sha256"
README_NAME = "AUTOROOT-README.txt"

# payloads/busybox-armhf is the exact Debian 1.35.0 static armhf build used in
# the working v4 run. Refuse to build a stick with a different binary.
EXPECTED_BUSYBOX_SHA256 = "9b89dbebc390b4b9174a449df18b422892387bf35717a63cf1e0aef5b4e8dcfe"

DEFAULT_HOST = os.environ.get("PHILIPS_TV_IP", "192.0.2.10")


class BuildError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_payload() -> Dict[str, str]:
    """Validate the two payload files and the single eval line."""
    if not AUTOROOT_SH.is_file():
        raise BuildError(f"missing payload script: {AUTOROOT_SH}")
    if not BUSYBOX.is_file():
        raise BuildError(f"missing busybox binary: {BUSYBOX}")
    if AUTOROOT_SH.stat().st_size == 0:
        raise BuildError(f"empty payload script: {AUTOROOT_SH}")

    busybox_sha = sha256_file(BUSYBOX)
    if busybox_sha != EXPECTED_BUSYBOX_SHA256:
        raise BuildError(
            "busybox-armhf SHA-256 mismatch\n"
            f"  expected: {EXPECTED_BUSYBOX_SHA256}\n"
            f"  actual:   {busybox_sha}\n"
            "Restore payloads/busybox-armhf from the known-good v4 dump."
        )

    # The host cannot execute the ARM binary. Presence of the applet name is a
    # cheap sanity check; the payload also runs busybox --list on the TV.
    if b"telnetd" not in BUSYBOX.read_bytes():
        raise BuildError("busybox-armhf does not contain the telnetd applet name")

    line = AUTOSCRIPT_LINE
    if line.count("\n") != 1 or not line.endswith("\n"):
        raise BuildError("autoscript must be exactly one LF-terminated line")
    if "#" in line:
        raise BuildError("autoscript must not contain '#': menu strips it as a comment")
    if line.split(None, 1)[0] in {"sleep", "id", "kid", "r", "OVERNIGHT"}:
        raise BuildError("autoscript starts with a menu special directive")

    return {
        "autoroot_sha256": sha256_file(AUTOROOT_SH),
        "busybox_sha256": busybox_sha,
    }


def build_manifest(target_dir: Path, hashes: Dict[str, str]) -> Dict[str, str]:
    """Write and return the hashes of every file staged on the stick."""
    manifest = {
        AUTOSCRIPT_NAME: hashlib.sha256(AUTOSCRIPT_LINE.encode("utf-8")).hexdigest(),
        "autoroot.sh": hashes["autoroot_sha256"],
        "busybox-armhf": hashes["busybox_sha256"],
    }
    lines = [f"{digest}  {name}\n" for name, digest in sorted(manifest.items())]
    (target_dir / MANIFEST_NAME).write_text("".join(lines), encoding="utf-8")
    return manifest


def stage_files(target_dir: Path) -> Dict[str, str]:
    """Copy the payload and the one-line autoscript into target_dir."""
    hashes = validate_payload()
    target_dir.mkdir(parents=True, exist_ok=True)

    (target_dir / AUTOSCRIPT_NAME).write_text(AUTOSCRIPT_LINE, encoding="utf-8")
    shutil.copy2(AUTOROOT_SH, target_dir / "autoroot.sh")
    shutil.copy2(BUSYBOX, target_dir / "busybox-armhf")

    # FAT has no POSIX mode. This is best-effort for a directory on a normal FS.
    try:
        os.chmod(target_dir / "autoroot.sh", 0o755)
        os.chmod(target_dir / "busybox-armhf", 0o755)
    except OSError:
        pass

    manifest = build_manifest(target_dir, hashes)
    (target_dir / README_NAME).write_text(
        "Titan OS autoroot stick\n"
        "=======================\n\n"
        "Cold boot the TV with this stick inserted. quick_debug/menu auto\n"
        "sleeps 30 seconds before it evaluates autoscript.txt, so the root\n"
        "port opens about 36 seconds after AC power-on. The payload path is\n"
        "hardcoded to /media/sda1: the stick must enumerate as sda, and it\n"
        "must have an empty FAT32 label.\n\n"
        "Connect with a raw client, not inetutils telnet:\n"
        "  nc <TV-IP> 2323\n"
        "  socat -,raw,echo=0 tcp:<TV-IP>:2323\n\n"
        "Then run: id\n"
        "Expected: uid=0(root) gid=0(root) groups=0(root) context=system_u:system_r:initrc_t\n\n"
        "Nothing is written to flash. Restore = remove the stick and cold boot.\n"
        "If it fails, read autoroot.log, autoroot-diag.txt, and FAILED on this stick.\n",
        encoding="utf-8",
    )

    os.sync()
    return manifest


def _require_root() -> None:
    if os.geteuid() != 0:
        raise BuildError("formatting a USB device requires root; run with sudo")


def _which_or_die(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise BuildError(f"required tool not found in PATH: {name}")
    return path


def _run(cmd: Iterable[str], *, input_text: Optional[str] = None, check: bool = True) -> subprocess.CompletedProcess:
    cmd = list(cmd)
    print("+ " + " ".join(cmd))
    return subprocess.run(cmd, input=input_text, text=True, check=check)


def _root_disk() -> Optional[str]:
    try:
        source = subprocess.check_output(
            ["findmnt", "-n", "-o", "SOURCE", "/"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    if not source:
        return None
    try:
        parent = subprocess.check_output(
            ["lsblk", "-no", "PKNAME", source], text=True
        ).strip().splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        parent = []
    if parent and parent[0]:
        return str(Path("/dev") / parent[0])
    return source


def _unmount_children(device: Path) -> None:
    try:
        rows = subprocess.check_output(
            ["lsblk", "-ln", "-o", "NAME,TYPE", str(device)], text=True
        ).splitlines()
    except subprocess.CalledProcessError:
        rows = []
    for row in rows:
        fields = row.split()
        if len(fields) >= 2 and fields[1] == "part":
            node = f"/dev/{fields[0]}"
            print(f"unmounting {node}")
            subprocess.run(["umount", node], check=False)
            subprocess.run(["umount", "-l", node], check=False)


def format_usb(device_arg: str, assume_yes: bool) -> Path:
    """Format a whole disk as MBR + one unlabelled FAT32 partition."""
    _require_root()
    for tool in (
        "sfdisk",
        "wipefs",
        "mkfs.fat",
        "partprobe",
        "lsblk",
        "mount",
        "umount",
        "findmnt",
    ):
        _which_or_die(tool)

    device = Path(device_arg)
    if not device.exists():
        raise BuildError(f"device does not exist: {device}")
    if not stat.S_ISBLK(os.stat(device).st_mode):
        raise BuildError(f"not a block device: {device}")

    root_disk = _root_disk()
    if root_disk and os.path.realpath(device) == os.path.realpath(root_disk):
        raise BuildError(f"refusing to format the disk that holds /: {device}")

    try:
        disk_type = subprocess.check_output(
            ["lsblk", "-dno", "TYPE", str(device)], text=True
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise BuildError(f"cannot inspect {device}: {exc}") from exc
    if disk_type != "disk":
        raise BuildError(
            f"{device} is a {disk_type!r}, not a whole disk; pass the disk device "
            "(e.g. /dev/sdb), not a partition (e.g. /dev/sdb1)"
        )

    size = subprocess.check_output(
        ["lsblk", "-dno", "SIZE,MODEL", str(device)], text=True
    ).strip()
    try:
        removable = subprocess.check_output(
            ["lsblk", "-dno", "RM", str(device)], text=True
        ).strip()
    except subprocess.CalledProcessError:
        removable = "?"
    print(f"Target: {device}  [{size}]  (kernel removable flag: {removable})")
    if removable == "0":
        print("WARNING: the kernel does not mark this device removable. Re-check the model above.")
    try:
        layout = subprocess.check_output(
            ["lsblk", "-o", "NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT", str(device)],
            text=True,
        ).rstrip()
        if layout:
            print(layout)
    except subprocess.CalledProcessError:
        pass
    print("This will ERASE the whole device and create MBR + one unlabelled FAT32 partition.")
    if not assume_yes:
        answer = input("Type YES to continue: ").strip()
        if answer != "YES":
            raise BuildError("aborted by user")

    _unmount_children(device)
    _run(["wipefs", "-a", str(device)])
    _run(
        ["sfdisk", "--force", "--label", "dos", str(device)],
        input_text=",,c,*\n",
    )
    subprocess.run(["partprobe", str(device)], check=False)
    subprocess.run(["blockdev", "--rereadpt", str(device)], check=False)
    subprocess.run(["udevadm", "settle"], check=False)

    name = device.name
    part = Path(f"{device}p1") if name and name[-1].isdigit() else Path(f"{device}1")
    for _ in range(20):
        if part.exists():
            break
        time.sleep(0.5)
    if not part.exists():
        raise BuildError(f"partition did not appear: {part}")

    _run(["mkfs.fat", "-F", "32", "-n", "", str(part)])

    # The autorun path is /media/sda1 only when mdev sees an empty label.
    label = subprocess.check_output(
        ["lsblk", "-no", "LABEL", str(part)], text=True
    ).strip()
    if label:
        fatlabel = shutil.which("fatlabel")
        if fatlabel:
            subprocess.run([fatlabel, str(part), ""], check=False)
            label = subprocess.check_output(
                ["lsblk", "-no", "LABEL", str(part)], text=True
            ).strip()
    if label:
        raise BuildError(
            f"filesystem label is {label!r}, but the TV only mounts an unlabelled "
            f"partition at /media/sda1; clear it with: fatlabel {part} ''"
        )
    return part


class _Mount:
    def __init__(self, part: Path):
        self.part = part
        self.mnt: Optional[Path] = None

    def __enter__(self) -> Path:
        self.mnt = Path(tempfile.mkdtemp(prefix="autoroot-usb-"))
        _run(["mount", "-t", "vfat", "-o", "rw", str(self.part), str(self.mnt)])
        return self.mnt

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.mnt is None:
            return
        subprocess.run(["sync"], check=False)
        subprocess.run(["umount", str(self.mnt)], check=False)
        subprocess.run(["umount", "-l", str(self.mnt)], check=False)
        try:
            self.mnt.rmdir()
        except OSError:
            pass


def verify_staged(part: Path, expected: Dict[str, str]) -> None:
    """Remount read-only and verify every committed file."""
    mnt = Path(tempfile.mkdtemp(prefix="autoroot-verify-"))
    try:
        _run(["mount", "-t", "vfat", "-o", "ro", str(part), str(mnt)])
        for name, digest in expected.items():
            path = mnt / name
            if not path.is_file():
                raise BuildError(f"verification failed: {name} missing after write")
            actual = sha256_file(path)
            if actual != digest:
                raise BuildError(
                    f"verification failed: {name} digest mismatch\n"
                    f"  expected: {digest}\n  actual:   {actual}"
                )
        print("verified on the stick: " + ", ".join(sorted(expected)))
    finally:
        subprocess.run(["umount", str(mnt)], check=False)
        try:
            mnt.rmdir()
        except OSError:
            pass


def print_next_steps(host: str, manifest: Dict[str, str]) -> None:
    print("\n" + "=" * 68)
    print("USB READY - ONE JOB: ROOT")
    print("=" * 68)
    print(f"autoscript.txt  {manifest[AUTOSCRIPT_NAME]}")
    print(f"autoroot.sh     {manifest['autoroot.sh']}")
    print(f"busybox-armhf   {manifest['busybox-armhf']}")
    print()
    print("1. Unplug the TV from AC and wait 10 seconds.")
    print("2. Insert this stick in the USB port that enumerates as sda on the TV.")
    print("   The payload path is hardcoded to /media/sda1; a second USB disk")
    print("   or a different hub port can make it sdb and the menu will miss it.")
    print("3. Plug the TV back in. The menu sleeps 30 s before eval, so :2323")
    print("   opens roughly 36 s after power-on. Wait at least 45 s before testing.")
    print()
    print("4. Connect with a raw client (inetutils telnet will show nothing):")
    print(f"     nc {host} 2323")
    print(f"     socat -,raw,echo=0 tcp:{host}:2323")
    print("   Then run: id")
    print("   Expected: uid=0(root) gid=0(root) groups=0(root) context=system_u:system_r:initrc_t")
    print()
    print("If it fails: pull the stick and read autoroot.log, autoroot-diag.txt, FAILED.")
    print("Restore: pull the stick and cold boot. Nothing is written to flash.")
    print("=" * 68)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Titan OS one-job autoroot USB (root shell on :2323)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-d",
        "--device",
        help="whole USB disk to format, e.g. /dev/sdb (NOT /dev/sdb1)",
    )
    group.add_argument(
        "--stage",
        metavar="DIR",
        help="stage into an existing directory without formatting (test/manual use)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="do not prompt before formatting the device",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"TV IP printed in the connect instructions (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="skip the post-write read-only remount verification",
    )
    args = parser.parse_args()

    try:
        if args.stage:
            manifest = stage_files(Path(args.stage))
            print(f"staged in {args.stage}")
            for name, digest in sorted(manifest.items()):
                print(f"  {digest}  {name}")
            print_next_steps(args.host, manifest)
            return 0

        validate_payload()
        part = format_usb(args.device, args.yes)
        # A desktop automounter may grab the new partition immediately.
        _unmount_children(Path(args.device))
        with _Mount(part) as mnt:
            manifest = stage_files(mnt)
        if not args.no_verify:
            expected = dict(manifest)
            verify_staged(part, expected)
        print_next_steps(args.host, manifest)
        return 0
    except BuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed ({exc.returncode}): {' '.join(exc.cmd)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
