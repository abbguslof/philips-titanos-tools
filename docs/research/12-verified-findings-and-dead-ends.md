# Verified findings and dead ends

One page to keep the claims honest. Target: `55PUS8000/12`, chassis
`TPA256E`/`TPN256E`, mainboard `715GD542`, firmware
`TPA256E_V056.002.236.191`.

## Verified

| Finding | Evidence |
| :--- | :--- |
| XBoot `2a4184c` -> ATF `a64m` -> Linux EL1 at `0x2800000` in ~90 ms. No interactive U-Boot. | [boot chain](01-boot-chain-xboot-atf.md), [serial log](../../evidence/hardware/xboot-serial.log) |
| Kernel command line uses `console=ttynull` and `root=/dev/mmcblk0p20`. | [v7 log](../../evidence/usb-autoroot/v7-autoroot-success/autoroot.log) |
| 40 user partitions; root p20, pstore p36, NVM p9, `apdat` p31. | [flash layout](02-flash-layout-and-partitions.md) |
| `mmcblk0boot0`/`boot1` are 4 MiB eMMC boot partitions holding XBoot. Vendor `boot0` is `mmcblk0p1`; `p1` `UMFG` value 0, `p2` value 1. | [UMFG slices](../../evidence/usb-autoroot/v5-umfg-partitions/) |
| `TIMG` container + `PIMG` components are MD5-only; inner `NFSB` uses SHA-256 + RSA-2048; `enc=gzip` decompresses to SquashFS LZO. | [firmware format](03-firmware-container-timg-pimg-nfsb.md) |
| `nvm_ubootdat.data` is 8,036 bytes with outer/inner IEEE CRC32; SAM writes p9 successfully. | [NVM format](04-uboot-nvm-format.md) |
| USB autorun: `S21idtv.sh` -> `run.sh` -> `quick_debug/menu auto` -> `eval` at ~36 s; empty label mounts at `/media/sda1`. | [USB hook](05-usb-autorun-hook.md) |
| Interactive `uid=0` over TCP `:2323` from a USB cold boot. | [v4](../../evidence/usb-autoroot/v4-shell-uid0/), [v7](../../evidence/usb-autoroot/v7-autoroot-success/) |
| Persistence via `/mtd_rwarea/apdat/customer_env.sh` survives a cold boot without the stick. | [persistence](06-persistence-customer-env.md), [pending capture](../../evidence/persistence/README.md) |
| JointSpace discovery, pairing, keys, volume, Ambilight, and `expert` LED injection work locally. | [JointSpace](08-jointspace-api.md) |
| `tvtype: consumer` blocks `/6/debug`/`/6/devtools` from LAN and loopback, regardless of pairing scope. `mds_mode=1` does not change it. | [JointSpace](08-jointspace-api.md) |
| Serial `SERV.U` TX works; RX never received a byte across a 25 s typed window. Serial break does not interrupt XBoot. | [hardware](07-hardware-serv-u.md) |
| `TPVisionDebug.cookie` / `enable_log2usb` are inert on this build. | [dead ends](#dead-ends) |

## Dead ends

| Vector | Result | Why |
| :--- | :--- | :--- |
| Serial break / `Ctrl-C` at power-on | **DEAD** | XBoot has no countdown; `uart mode:0`. |
| Interactive serial getty | **DEAD** | `ttyS0` RX is 0; no input consumer. |
| `uart_mode=1` in NVM | **DEAD** | XBoot ignores the NVM variable. |
| `bootdelay=5` in NVM | **Inert** | No interactive U-Boot prompt. |
| `mds_mode=1` / `server_env=dev` in NVM | **TESTED-NEGATIVE** | Userspace `tvtype: consumer` gate; SAM snaps back to `Prod`. |
| JointSpace engineering routes from LAN | **DEAD** | 403 due to `tvtype`, not an IP ACL. |
| JointSpace engineering routes from loopback | **DEAD** | Same userspace gate. |
| `POST /6/activities/browser` | **Stub** | Returns 200 `{}`; no standalone browser. |
| TLS hijack of `eu.app.titanos.tv` with a private CA | **DEAD** | `DP_203`; private CA/pinning rejection. Breaking the origin also prevents the launcher/input field from rendering; the keyboard assets themselves are local. |
| `TPVisionDebug.cookie` / `enable_log2usb` | **Inert** | No daemon references them on Titan OS. |
| `BrowserIpcPluginClass` from a plain HTTP origin | **Inert** | Exposes 0 native methods outside the authorized origin. |
| Channel-map `usr/` traversal | **OPEN** | No verified code-execution path. |
| Hardware eMMC ISP / voltage glitch | **NOT ATTEMPTED** | High brick risk; not needed for this path. |
| `init=` injection | **FORBIDDEN** | No serial/physical recovery; can brick before SAM. |

## Open questions

- The exact source of XBoot's `uart mode:0` print is not proven. The vendor
  script reads `UMFG`/`DEBUG_FUNC_LEVEL` from `/dev/nvt-part-name/boot0`, but
  XBoot still reports mode 0 with the observed slices.
- Whether a future firmware build keeps the same `quick_debug/menu auto` hook.
- Whether the user trust store can be extended from USB to defeat `DP_203`.
- Whether the channel-map import parser has a memory-safety bug. Not tested.

## What the root path does not do

- It does not modify the read-only rootfs or the bootloader.
- It does not defeat the `NFSB` RSA/SHA-256 layer.
- It does not bypass Widevine/DRM.
- It does not provide remote access without a listener you start yourself.
