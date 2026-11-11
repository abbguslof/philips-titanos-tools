# Verified findings and dead ends

One page to keep the claims honest. Target: `55PUS8000/12`, chassis
`TPA256E`/`TPN256E`, mainboard `715GD542`, firmware
`TPA256E_V056.002.236.191`.

## Verified

| Finding | Evidence |
| :--- | :--- |
| XBoot `2a4184c` -> ATF `a64m` -> Linux EL1 at `0x2800000` in ~90 ms. No interactive U-Boot. | [boot chain](01-boot-chain-xboot-atf.md), [serial log](../../evidence/hardware/xboot-serial.log) |
| Kernel command line uses `console=ttynull` and `root=/dev/mmcblk0p20`. | [v7 log](../../evidence/usb-autoroot/v7-autoroot-success/autoroot.log) |
| 40 user partitions; root p20, pstore p36, `misc` p9, `nvm_dat` p11, `apdat` p31. | [flash layout](02-flash-layout-and-partitions.md), [partition map](../reference/partition-map.md) |
| `mmcblk0boot0`/`boot1` are 4 MiB eMMC boot partitions holding XBoot. Vendor `boot0` is `mmcblk0p1`; `p1` `UMFG` value 0, `p2` value 1. | [UMFG slices](../../evidence/usb-autoroot/v5-umfg-partitions/) |
| `TIMG` container + `PIMG` components are MD5-only; inner `NFSB` uses SHA-256 + RSA-2048; `enc=gzip` decompresses to SquashFS LZO. | [firmware format](03-firmware-container-timg-pimg-nfsb.md) |
| `nvm_ubootdat.data` is an 8,036-byte wrapper with outer/inner IEEE CRC32 and partition ID 9; the live raw NVM variables are in `nvm_dat` (p11); SAM writes the NVM area p9 successfully. | [NVM format](04-uboot-nvm-format.md) |
| The inner SquashFS at offset `0x1000` mounts directly with `mount -t squashfs`; the NFSB verifier runs only for the `nfsb` mount. | [runtime NFSB](17-runtime-nfsb-squashfs.md), [evidence](../../evidence/runtime-nfsb/) |
| A modified NFSB copy still mounts through `nfsb` with a valid header, but dm-verity rejects the changed block on read. | [runtime NFSB](17-runtime-nfsb-squashfs.md), [evidence](../../evidence/runtime-nfsb/) |
| USB autorun: `S21idtv.sh` -> `run.sh` -> `quick_debug/menu auto` -> `eval` at ~36 s; empty label mounts at `/media/sda1`. | [USB hook](05-usb-autorun-hook.md) |
| Interactive `uid=0` over TCP `:2323` from a USB cold boot. | [v4](../../evidence/usb-autoroot/v4-shell-uid0/), [v7](../../evidence/usb-autoroot/v7-autoroot-success/) |
| Persistence via `/mtd_rwarea/apdat/customer_env.sh` survives a cold boot without the stick. | [persistence](06-persistence-customer-env.md), [pending capture](../../evidence/persistence/README.md) |
| JointSpace discovery, pairing, keys, volume, Ambilight, and `expert` LED injection work locally. | [JointSpace](08-jointspace-api.md) |
| `tvtype: consumer` blocks `/6/debug`/`/6/devtools` from LAN and loopback, regardless of pairing scope. `mds_mode=1` does not change it. | [JointSpace](08-jointspace-api.md) |
| Serial `SERV.U` TX works; RX never received a byte across a 25 s typed window. Serial break does not interrupt XBoot. | [hardware](07-hardware-serv-u.md) |
| Root shell runs as `initrc_t`; `runcon -t unconfined_t` is allowed, `init_t`/`kernel_t` are denied. `CapEff=0x1ffffffffff`. | [SELinux runtime](15-selinux-runtime-control.md) |
| A `bin_t` copy of `/bin/mount` in `unconfined_t` mounts non-mountpoint targets; `mounton` over the stock `com.tpv.opera`/`com.nvt.appmgr` mountpoints was denied under the stock policy. The permissive v33 policy now allows it. | [SELinux runtime](15-selinux-runtime-control.md) |
| A single `dd bs=1048576 count=1` write loads the stock v30 policy and a converted v33 policy; `cat` splits at 128 KiB and fails with `ebitmap: truncated map`. | [SELinux runtime](15-selinux-runtime-control.md) |
| A v33 policy with all 1120 types permissive loads at boot from `customer_env.sh`; `mounton` over an `appmgr_t` target then succeeds. `getenforce` still reports `Enforcing`. | [SELinux runtime](15-selinux-runtime-control.md) |
| Stock Settings/native menus work after the stock rollback, permissive policy, and a cold boot (user report 2026-11-01). Only the intentional Pi-hole `titanos.tv` block remains. | [SELinux runtime](15-selinux-runtime-control.md) |
| `/mtd_apexe/board/modules` contains matching vendor `.ko` files; `modules_disabled=0`; unsigned `ndp_nvtmem.ko` loads and unloads with `insmod`/`rmmod`; `vermagic` includes `modversions aarch64`. | [Kernel/module control](16-kernel-and-hardware-control.md) |
| A patched `ndp_logo.ko` carrier executes arbitrary unsigned kernel code; a relocation-safe payload read `selinux_state` (`0x01010100`) and wrote `initialized=0` (`0x01010000`), then restored it. | [Kernel/module control](16-kernel-and-hardware-control.md) |
| A persistent seloff carrier at `/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko` loads from `customer_env.sh` and clears `selinux_state.initialized`; two cold boots verified TV/appmgr/idtv. A `no_kernel_module` file skips it. | [Kernel/module control](16-kernel-and-hardware-control.md) |
| `/dev/mem`/`/dev/kmem` mknod but open with `ENODEV`; `/proc/kcore`, `/proc/config.gz`, BTF, and `/proc/kexec*` are absent. `/sys/fs/selinux/disable` is `EINVAL`; `selinux_state` is the only SELinux global. | [Kernel/module control](16-kernel-and-hardware-control.md) |
| `/dev/ntkmem`, `/dev/ndp_hwmem`, `/dev/ntgpio`, `/dev/ntkiic0`, `/dev/i2c-*`, `/dev/ntkled`, `/dev/ntktcon`, `/dev/ntkhdmi`, `/dev/uinput`, and `/dev/uhid` exist; `/dev/input` only has `mice`. | [Kernel/module control](16-kernel-and-hardware-control.md) |
| `kexec`, `/dev/mem`, `/dev/kmem`, `/proc/kcore`, and `/lib/modules` are absent; `insmod` exists; `security_hook_heads`/`security_add_hooks`/`selinux_state` are visible with `kptr_restrict=0`. | [SELinux runtime](15-selinux-runtime-control.md) |
| NVM p9 has no `bootargs`/`selinux`/`enforcing`; the kernel command line is in the FDT/ATF. | [SELinux runtime](15-selinux-runtime-control.md) |
| `mmcblk0boot0` is readable (4 MiB); `policy33.bin` and `boot0.bin` were copied to `/swdl`. | [SELinux runtime](15-selinux-runtime-control.md) |
| `TPVisionDebug.cookie` / `enable_log2usb` are inert on this build. | [dead ends](#dead-ends) |

### External reports

| Finding | Evidence |
| :--- | :--- |
| On `55PUS8450/12`, firmware `TPN256E_V056.010.032.001`, `run.sh` does not source `customer_env.sh`; the vendor `/swdl/telnet/telnetd` seam restores USB-less persistence. **REPORTED**, not independently reproduced. | [variant note](24-swdl-telnet-persistence-2026-11-11.md) |

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
| Chromium DevTools `:7788` | **OPEN / exposed** | Browser runs with `--remote-debugging-port=7788`; LAN reachability and CDP actions are a debug surface, not a root path. |
| TLS hijack of `eu.app.titanos.tv` with a private CA | **DEAD** | `DP_203`; private CA/pinning rejection. Breaking the origin also prevents the launcher/input field from rendering; the keyboard assets themselves are local. |
| `TPVisionDebug.cookie` / `enable_log2usb` | **Inert** | No daemon references them on Titan OS. |
| `BrowserIpcPluginClass` from a plain HTTP origin | **Inert** | Exposes 0 native methods outside the authorized origin. |
| Channel-map `usr/` traversal | **OPEN** | No verified code-execution path. |
| Hardware eMMC ISP / voltage glitch | **NOT ATTEMPTED** | High brick risk; not needed for this path. |
| `setenforce 0` / `/sys/fs/selinux/disable` | **DEAD** | Kernel returns `EINVAL`; `/etc/selinux/config` read-only. |
| NVM `selinux=0` / `enforcing=0` | **DEAD** | The NVM area (`nvm_dat`/p11 and the SAM wrapper) has no `bootargs`; the cmdline is in the FDT/ATF. |
| `/sys/fs/selinux/load` of the running policy via `cat` | **DEAD** | 128 KiB chunks; `ebitmap: truncated map`. Use one `dd bs=1048576 count=1`. |
| `mount`/`umount` under `unconfined_t` | **SUPERSEDED** | A permissive v33 policy now allows `mounton`; the `bin_t`/`unconfined_t` workaround is only a fallback. |
| `kexec`, `/dev/mem`, `/proc/kcore`, kernel module | **DEAD** | kexec/device nodes absent; no `/lib/modules`; no matching build. |
| `init=` injection | **FORBIDDEN** | No serial/physical recovery; can brick before SAM. |

## Open questions

- The exact source of XBoot's `uart mode:0` print is not proven. The vendor
  script reads `UMFG`/`DEBUG_FUNC_LEVEL` from `/dev/nvt-part-name/boot0`, but
  XBoot still reports mode 0 with the observed slices.
- Whether a future firmware build keeps the same `quick_debug/menu auto` hook.
- Whether the user trust store can be extended from USB to defeat `DP_203`.
- Whether the channel-map import parser has a memory-safety bug. Not tested.
- Whether the two v33-only netlink permissions (`nlmsg_readpriv`,
  `nlmsg_getneigh`) matter to any running service. They remain denied.
- Whether to restore `app.titanos.tv`/`eu.app.titanos.tv` in Pi-hole or keep the
  cloud blocked. The TV is otherwise working.
- Whether the eMMC `boot_area` can be switched for recovery.
- Whether the boot-time NFSB verifier can be bypassed without the vendor RSA
  key. The runtime raw mount does not attempt it; the `NVHC` and encrypted boot
  images add more checks.

## What the root path does not do

- It does not modify the read-only rootfs or the bootloader.
- It does not defeat the boot-time `NFSB` RSA/SHA-256 layer. The runtime raw
  SquashFS mount is a separate read-only userspace path; a modified NFSB image
  still cannot boot or flash.
- It does not bypass Widevine/DRM.
- It does not provide remote access without a listener you start yourself.
- It does not flip the kernel's global enforcing flag: `getenforce` still says
  `Enforcing` and `setenforce` is `EINVAL`. It does load a v33 policy with every
  type permissive, so enforcement is effectively off without a boot-chain write.
