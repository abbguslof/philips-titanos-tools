# Payloads

| File | Purpose |
| :--- | :--- |
| `autoscript.autoroot.txt` | One-line autoscript staged by `tools/autoroot_usb.py`. |
| `autoroot.sh` | USB root payload: diagnostics, BusyBox, firewall, `telnetd` on `:2323`, `READY`. |
| `persist_root.sh` | Installs the `customer_env.sh` persistence hook. |
| `nfsb_raw_mount.sh` | Read-only mount of the SquashFS inside an NFSB partition. Run on the TV as root. |
| `autoscript.diag.txt` | Older, broader diagnostic autoscript from the v4 research runs. Not the canonical autoroot payload. |
| `busybox-armhf` | Static ARM hard-float BusyBox 1.35.0 (Debian). GPLv2; see `THIRD_PARTY_NOTICES.md`. |
| `bootstrap/bootstrap.sh` | Legacy generic reverse-shell example. Not used by the verified root path. |

## Which one do I use?

- **Ephemeral root from a cold boot:** `tools/autoroot_usb.py` stages
  `autoscript.autoroot.txt` + `autoroot.sh` + `busybox-armhf`.
- **Persistence after root:** run `persist_root.sh` from the root shell.
- **Diagnostics:** `autoscript.diag.txt` is a historical superset; it is not
  staged by the current tool.
- **Read-only filesystem inspection:** run
  `nfsb_raw_mount.sh <partition> <mountpoint>` on the TV as root. The tool
  copies the partition from offset `0x1000` to `/tmp`, attaches the copy
  read-only, and mounts it with `squashfs`. It does not write the partition or
  make a modified image bootable.

## BusyBox

BusyBox resolves applets from `argv[0]`. The binary must be named `busybox`.
The USB payload copies it to `/tmp/busybox`; the persistent hook copies it to
`/tmp/persist/busybox` so a USB stick left in the TV cannot overwrite the
running persistent binary.

## Safety

The payloads do not flush the firewall, do not use `pkill`, and do not write to
the read-only rootfs. The persistent installer writes only under
`/mtd_rwarea/apdat` and `/tmp`. The raw NFSB mount copies to `/tmp` and mounts
read-only; it does not write the source partition.
