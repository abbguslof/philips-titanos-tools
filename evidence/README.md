# Evidence Index

Curated, redacted proof runs. Raw captures and full device dumps are kept in the
private research archive. See [REDACTION.md](REDACTION.md) for what was removed.

## USB autorun

| Set | What it proves | Key files |
| :--- | :--- | :--- |
| [v1-ttyS0-diag](usb-autoroot/v1-ttyS0-diag/) | The autoscript runs as root and `/dev/ttyS0` exists. | `proof.txt` |
| [v2-pty-rx](usb-autoroot/v2-pty-rx/) | `ttyS0` RX stays 0; BusyBox argv[0] issue. | `d/diag.txt`, `d/getty.txt`, `d/telnetd.txt` |
| [v3-telnetd-listen](usb-autoroot/v3-telnetd-listen/) | `telnetd` listens on `:2323`; local connect works; RX still 0. | `d/net3.txt`, `d/tlocal.txt`, `d/rx_*` |
| [v4-shell-uid0](usb-autoroot/v4-shell-uid0/) | **First interactive `uid=0` proof** over TCP. | `d/tl4.txt`, `d/net4.txt` |
| [v5-umfg-partitions](usb-autoroot/v5-umfg-partitions/) | 32-byte `UMFG` slices at `0x1A0200` in p1/p2. | `p1-umfg-0x1a0200.bin`, `p2-umfg-0x1a0200.bin` |
| [v6-regression](usb-autoroot/v6-regression/) | The stick was missing `busybox-armhf`; script ran, `telnetd` did not. | `d/net4.txt` (empty), `d/tl4.txt` (refused) |
| [v7-autoroot-success](usb-autoroot/v7-autoroot-success/) | Full cold-boot success: `uid=0`, `:2323`, `READY`. | `autoroot.log`, `autoroot-diag.txt`, `READY` |
| [v8-stateproof](usb-autoroot/v8-stateproof/) | Non-resetting autoscript writes one boot block per cold boot. | `proof.txt`, `run-meta.txt` |

## External firmware variant

| Set | What it proves |
| :--- | :--- |
| [tpn256e-variant](tpn256e-variant/) | External USB autoroot on `55PUS8450/12`; it does not prove the `/swdl` hook after a USB-less boot. |

## Hardware and firmware

| Set | What it proves |
| :--- | :--- |
| [hardware/xboot-serial.log](hardware/xboot-serial.log) | XBoot -> ATF -> EL1, `uart mode:0`, boot timing. |
| [firmware/upgrade_loader.html](firmware/upgrade_loader.html) | The historical Google Drive mirror returned a virus-scan warning page, not a loader. |

## Deep boot chain

| Set | What it proves |
| :--- | :--- |
| [deep/2026-11-12](deep/2026-11-12-8000-bootchain.md) | Read-only 8000 boot map: protected A/B secure slots; plain `p21` `kerupm` upgrade kernel; `p1/p2` UMFG slots; `p9` slot map; package-to-live matches and update environment. |

Raw partitions and NVM remain under `dist/` and are not published. See
[boot image map](../docs/research/28-boot-image-map.md) and [update package map](../docs/research/29-update-package-map.md).

## Runtime NFSB

| Set | What it proves |
| :--- | :--- |
| [runtime-nfsb](runtime-nfsb/) | A pristine NFSB mount verifies the header and creates verity targets; a modified block fails verity on read; the inner SquashFS at offset `0x1000` mounts directly with `squashfs`. |

The method and limits are in
[runtime NFSB bypass](../docs/research/17-runtime-nfsb-squashfs.md).

## Persistence

The persistent `customer_env.sh` hook was verified on hardware: after installing
it, removing the USB, and cold booting, the `:2323` root shell returned. The
redacted capture is [persistence/output.txt](persistence/output.txt): `uid=0`,
`system_u:system_r:initrc_t`, `telnetd pid 1500`, `READY`, listener on `:2323`,
and the explicit `:2323` ACCEPT rule. See
[persistence/README.md](persistence/README.md) for the procedure.

## Install and SSH

| Set | What it proves |
| :--- | :--- |
| [install/proof-1.txt](install/proof-1.txt) | A static `lsblk` runs from `/mtd_rwarea/apdat/opt/bin`. |
| [install/proof-2.txt](install/proof-2.txt) | The prefix and `PATH` survive a USB-less cold boot. |
| [install/ssh-build.txt](install/ssh-build.txt) | Static aarch64 Dropbear build provenance. |
| [install/ssh-live.txt](install/ssh-live.txt) | Key-only SSH, `PATH`, and the three failures and fixes. |
| [install/ssh-boot.txt](install/ssh-boot.txt) | SSH works after a USB-less cold boot. |

## Live inventory

| Set | What it proves |
| :--- | :--- |
| [live-inventory/phase-a-2026-11-09.txt](live-inventory/phase-a-2026-11-09.txt) | Redacted boot, SELinux, mount, device, and tooling census. |

## Evidence rules

- One claim per set; keep the smallest file that proves it.
- Redact serials, MACs, SSIDs, IPs, PINs, and credentials.
- Keep full partition dumps and raw pcaps out of the public tree.
- Update this index when adding or removing a set.
