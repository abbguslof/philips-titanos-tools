#!/usr/bin/env python3
"""
Philips Titan OS USB Staging & Pre-Flight Tool

Prepares, verifies, and stages payload files onto a FAT32 USB drive
for Service Alignment Mode (SAM) 'Download from USB'.

Includes safety checks, Canary test mode (zero-brick risk verification),
and automatic dual-CRC32 integrity validation.
"""

import argparse
import os
import shutil
import sys
from typing import Dict, List, Optional

# Ensure repository root is in sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tools.uboot_nvm_tool import UBootNVM
from tools.edid_tool import verify_edid_nvm

FACTORY_SAM = os.path.join(REPO_ROOT, "samples", "nvm")
FACTORY_CHANNELS = os.path.join(REPO_ROOT, "samples", "channel-maps")
FACTORY_UBOOT = os.path.join(FACTORY_SAM, "nvm_ubootdat.data")
FACTORY_EDID = os.path.join(FACTORY_SAM, "nvm_edid.data")


def verify_factory_assets():
    """Confirms pristine factory assets exist and pass checksums."""
    if not os.path.exists(FACTORY_UBOOT):
        sys.exit(f"Error: Factory U-Boot file missing at {FACTORY_UBOOT}")
    if not os.path.exists(FACTORY_EDID):
        sys.exit(f"Error: Factory EDID file missing at {FACTORY_EDID}")

    nvm = UBootNVM.from_file(FACTORY_UBOOT)
    i_ok, o_ok, _, _, _, _ = nvm.verify()
    if not (i_ok and o_ok):
        sys.exit("CRITICAL ERROR: Factory U-Boot dump failed internal verification!")

    with open(FACTORY_EDID, "rb") as f:
        e_ok, _, _ = verify_edid_nvm(f.read())
    if not e_ok:
        sys.exit("CRITICAL ERROR: Factory EDID dump failed internal verification!")


def stage_drive(
    target_dir: str,
    mode: str,
    custom_vars: List[str],
    include_channels: bool = True,
    debug_cookie: bool = False,
):
    verify_factory_assets()

    # 0. Optional TPVision diagnostic logging tokens
    if debug_cookie:
        cookie_path = os.path.join(target_dir, "TPVisionDebug.cookie")
        log2usb_path = os.path.join(target_dir, "enable_log2usb")
        with open(cookie_path, "w") as f:
            f.write("")
        with open(log2usb_path, "w") as f:
            f.write("")
        print(f"✓ Staged Diagnostic Tokens on USB Root:")
        print(f"  - {cookie_path}")
        print(f"  - {log2usb_path}")

    sam_dir = os.path.join(target_dir, "SAM")
    os.makedirs(sam_dir, exist_ok=True)

    # 1. Copy pristine EDID
    staged_edid = os.path.join(sam_dir, "nvm_edid.data")
    shutil.copy2(FACTORY_EDID, staged_edid)
    print(f"✓ Staged EDID: {staged_edid} (932 bytes)")

    # 2. Prepare U-Boot NVM
    nvm = UBootNVM.from_file(FACTORY_UBOOT)
    staged_uboot = os.path.join(sam_dir, "nvm_ubootdat.data")

    if mode == "stock":
        print("  Mode: STOCK (Pristine factory backup, no modifications)")
    elif mode == "canary":
        print("  Mode: CANARY (Safe non-destructive test variable)")
        print("  Injecting: 'canary_test=1' to safely verify NVM write capability.")
        nvm.variables["canary_test"] = "1"
        if "canary_test" not in nvm.var_order:
            nvm.var_order.append("canary_test")
    elif mode == "diag":
        print("  Mode: DIAGNOSTIC (Safe engineering flags: mds_mode, watchdog, telnet/debug)")
        diag_flags = {
            "bootdelay": "5",
            "canary_test": "1",
            "mds_mode": "1",
            "watch_dog_timeout": "0",
            "sw_debug": "1",
            "telnet_enable": "1",
            "debug_enable": "1",
            "iptables_disable": "1",
            "server_env": "dev",
        }
        for k, v in diag_flags.items():
            nvm.variables[k] = v
            if k not in nvm.var_order:
                nvm.var_order.append(k)
            print(f"  Injected: {k} = {v}")
    elif mode == "custom":
        print("  Mode: CUSTOM")
        for kv in custom_vars:
            if "=" not in kv:
                sys.exit(f"Error: Custom variable '{kv}' must be in KEY=VALUE format.")
            k, v = kv.split("=", 1)
            nvm.variables[k] = v
            if k not in nvm.var_order:
                nvm.var_order.append(k)
            print(f"  Injected: {k} = {v}")

    # Build and save
    nvm.save(staged_uboot)
    print(f"✓ Staged U-Boot NVM: {staged_uboot} ({nvm.raw_size} bytes)")

    # Verify staged file directly on disk
    staged_obj = UBootNVM.from_file(staged_uboot)
    i_ok, o_ok, sin, cin, sout, cout = staged_obj.verify()
    if not (i_ok and o_ok):
        sys.exit("CRITICAL ERROR: Staged U-Boot binary failed CRC32 verification!")
    print(f"  Inner CRC32: 0x{sin:08x} (calc: 0x{cin:08x}) -> PASS")
    print(f"  Outer CRC32: 0x{sout:08x} (calc: 0x{cout:08x}) -> PASS")

    # 3. Channel Maps & Traversal Canary
    if include_channels and os.path.exists(FACTORY_CHANNELS):
        staged_chan = os.path.join(target_dir, "PhilipsChannelMaps")
        if os.path.exists(staged_chan):
            shutil.rmtree(staged_chan)
        shutil.copytree(FACTORY_CHANNELS, staged_chan)
        # Stage Option 2 Canary inside ChannelMap_100/usr/
        usr_dir = os.path.join(staged_chan, "ChannelMap_100", "usr")
        os.makedirs(usr_dir, exist_ok=True)
        canary_file = os.path.join(usr_dir, "canary_test.txt")
        with open(canary_file, "w") as f:
            f.write("CANARY_TEST_OK_TITAN_TOOLS\nImported from ChannelMap_100/usr/ to test directory traversal.\n")
        print(f"✓ Staged Channel Maps & Traversal Canary: {canary_file}")

    # Media player keepalive image (prevents TV media player auto-dismissing drive as 'empty')
    sample_jpg = os.path.join(target_dir, "media_keepalive.jpg")
    try:
        with open(sample_jpg, "wb") as f:
            f.write(
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
                b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c"
                b"\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c"
                b"(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
                b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00"
                b"\xbf\x00\xff\xd9"
            )
        print(f"✓ Staged Media Keepalive Image (prevents 'empty drive' popup): {sample_jpg}")
    except Exception as e:
        pass

    # 4. Bootstrap Payload Scripts
    bootstrap_src = os.path.join(REPO_ROOT, "tools", "bootstrap")
    if os.path.exists(bootstrap_src):
        bootstrap_dst = os.path.join(target_dir, "bootstrap")
        if os.path.exists(bootstrap_dst):
            shutil.rmtree(bootstrap_dst)
        shutil.copytree(bootstrap_src, bootstrap_dst)
        print(f"✓ Staged Bootstrap payload to {bootstrap_dst}")

    # 5. Local File Origin Diagnostic Page
    debug_usb_src = os.path.join(REPO_ROOT, "tools", "debug_usb.html")
    if os.path.exists(debug_usb_src):
        debug_usb_dst = os.path.join(target_dir, "debug_usb.html")
        shutil.copy2(debug_usb_src, debug_usb_dst)
        print(f"✓ Staged USB Local Diagnostic Page to {debug_usb_dst}")

    # Force write sync
    if hasattr(os, "sync"):
        os.sync()

    print("\n" + "=" * 60)
    print("🎯 PRE-FLIGHT VERIFICATION COMPLETE: USB IS READY!")
    print("=" * 60)
    print(f"Destination:     {target_dir}")
    print(f"SAM Folder:      {sam_dir}")
    print(f"U-Boot Checksum: Outer=0x{sout:08x}, Inner=0x{sin:08x}")
    print("-" * 60)
    print("NEXT STEPS ON THE TV:")
    print("1. Safely unmount/eject the USB drive from your PC.")
    print("2. Insert the USB drive into USB PORT 1 on the TV.")
    print("3. Tune TV to an active HDMI input.")
    print("4. Press '123' -> Enter '062596' -> Press '123' -> Press 'Info'.")
    print("5. In SAM, scroll to 'Download from USB' and press OK.")
    print("6. Wait for the transfer to complete, then power-cycle the TV.")
    print("=" * 60)


def resolve_target_dir(target: Optional[str]) -> str:
    user = os.environ.get("USER", "")

    # 1. If explicit path provided
    if target:
        # Check if block device passed (e.g. /dev/sda1 or /dev/sda)
        if target.startswith("/dev/"):
            dev = target if target[-1].isdigit() else (target + "1")
            import subprocess
            res = subprocess.run(["findmnt", "-n", "-o", "TARGET", dev], capture_output=True, text=True)
            mnt = res.stdout.strip()
            if mnt and os.path.isdir(mnt):
                return mnt
            # Try mounting via udisksctl
            mount_res = subprocess.run(["udisksctl", "mount", "-b", dev], capture_output=True, text=True)
            res2 = subprocess.run(["findmnt", "-n", "-o", "TARGET", dev], capture_output=True, text=True)
            mnt2 = res2.stdout.strip()
            if mnt2 and os.path.isdir(mnt2):
                return mnt2

        # Check Arch / Fedora / modern systemd /run/media/ redirection
        if target.startswith("/media/") and not os.path.exists(target):
            alt = target.replace("/media/", "/run/media/", 1)
            if os.path.isdir(alt):
                print(f"ℹ️  Redirected '{target}' -> '{alt}' (Arch Linux /run/media path)")
                return alt

        if os.path.isdir(target):
            return target

    # 2. Auto-detect mounted volume labeled PHILIPS or USB_DRIVE
    candidates = [
        f"/run/media/{user}/PHILIPS",
        f"/media/{user}/PHILIPS",
        f"/run/media/{user}/USB_DRIVE",
        f"/media/{user}/USB_DRIVE",
        "/run/media/PHILIPS",
        "/media/PHILIPS",
    ]
    for c in candidates:
        if os.path.isdir(c):
            print(f"✓ Auto-detected mounted USB drive at '{c}'")
            return c

    sys.exit(
        f"Error: Target directory '{target}' does not exist or is not mounted.\n"
        f"Make sure your USB drive is plugged in and mounted (e.g. at /run/media/{user}/PHILIPS)."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Philips Titan OS USB Staging & Pre-Flight Tool"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="USB mountpoint or staging directory (defaults to auto-detecting volume labeled PHILIPS)",
    )
    parser.add_argument(
        "--target",
        "-t",
        dest="target_flag",
        default=None,
        help="USB mountpoint or staging directory (alias for target argument)",
    )

    group = parser.add_argument_group("Staging Mode Selection")
    group.add_argument(
        "--mode",
        "-m",
        choices=["diag", "canary", "stock", "custom"],
        default=None,
        help="Staging mode: diag (diagnostic), canary (test), stock (factory), custom",
    )
    group.add_argument(
        "--diag",
        action="store_true",
        help="Stage diagnostic NVM flags (mds_mode, watchdog, sw_debug, telnet_enable). These do not unlock the userspace JointSpace tvtype gate.",
    )
    group.add_argument(
        "--canary",
        action="store_true",
        help="Stage safe Canary test (injects 'canary_test=1' with zero brick risk)",
    )
    group.add_argument(
        "--stock",
        action="store_true",
        help="Stage 100% pristine factory backup (for restore test)",
    )
    group.add_argument(
        "--set",
        nargs="+",
        metavar="KEY=VALUE",
        help="Inject custom variables into U-Boot NVM",
    )

    parser.add_argument(
        "--no-channels",
        action="store_true",
        help="Skip staging PhilipsChannelMaps directory",
    )
    parser.add_argument(
        "--debug-cookie",
        action="store_true",
        help="Legacy/inert on Titan OS: stage TPVisionDebug.cookie and enable_log2usb anyway",
    )

    args = parser.parse_args()

    target_arg = args.target_flag or args.target
    target_dir = resolve_target_dir(target_arg)

    if args.mode:
        mode = args.mode
    elif args.diag:
        mode = "diag"
    elif args.canary:
        mode = "canary"
    elif args.stock:
        mode = "stock"
    elif args.set:
        mode = "custom"
    else:
        sys.exit(
            "Error: Please specify staging mode:\n"
            "  --diag (or --mode diag)\n"
            "  --canary (or --mode canary)\n"
            "  --stock (or --mode stock)\n"
            "  --set KEY=VALUE"
        )
    stage_drive(
        target_dir=target_dir,
        mode=mode,
        custom_vars=args.set or [],
        include_channels=not args.no_channels,
        debug_cookie=args.debug_cookie,
    )


if __name__ == "__main__":
    main()
