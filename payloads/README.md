# Payloads

| File | Purpose |
| :--- | :--- |
| `autoscript.autoroot.txt` | One-line autoscript staged by `tools/autoroot_usb.py`. |
| `autoroot.sh` | USB root payload: diagnostics, BusyBox, firewall, `telnetd` on `:2323`, `READY`. |
| `persist_root.sh` | Installs the `customer_env.sh` persistence hook. |
| `autoscript.diag.txt` | Older, broader diagnostic autoscript from the v4 research runs. Not the canonical autoroot payload. |
| `busybox-armhf` | Static ARM hard-float BusyBox 1.35.0 (Debian). GPLv2; see `THIRD_PARTY_NOTICES.md`. |
| `bootstrap/bootstrap.sh` | Legacy generic reverse-shell example. Not used by the verified root path. |

## Which one do I use?

- **Ephemeral root from a cold boot:** `tools/autoroot_usb.py` stages
  `autoscript.autoroot.txt` + `autoroot.sh` + `busybox-armhf`.
- **Persistence after root:** run `persist_root.sh` from the root shell.
- **Diagnostics:** `autoscript.diag.txt` is a historical superset; it is not
  staged by the current tool.

## BusyBox

BusyBox resolves applets from `argv[0]`. The binary must be named `busybox`.
The USB payload copies it to `/tmp/busybox`; the persistent hook copies it to
`/tmp/persist/busybox` so a USB stick left in the TV cannot overwrite the
running persistent binary.

## Safety

The payloads do not flush the firewall, do not use `pkill`, and do not write to
the read-only rootfs. The persistent installer writes only under
`/mtd_rwarea/apdat` and `/tmp`.
