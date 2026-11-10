# Live inventory (Phase A)

Status: **VERIFIED / DRIFT** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-09.

Read-only enumeration of the live `uid=0` shell over `:2323`. No writes, no
`insmod`, no partition access. Evidence: redacted transcript under
`evidence/live-inventory/phase-a-2026-11-09.txt`.

Target hostname is `n22074_linux_tk`. Values that are hardware- or
implementation-specific are labeled inline; anything not observed stays
`UNKNOWN`.

## Identity and kernel

| Fact | Value | Label |
| :--- | :--- | :--- |
| uid/gid | `uid=0(root) gid=0(root) groups=0(root)` | VERIFIED |
| SELinux context on `id` | not printed this run (seloff active; see below) | UNKNOWN |
| `uname -a` | `Linux n22074_linux_tk 6.1.124-gd063554eebf5-ab6 #4 SMP PREEMPT Tue May 27 11:36:10 CST 2025 aarch64` | VERIFIED |
| Toolchain | Android clang 17.0.2 (10087095), LLD 17.0.2, `root@oabuild59` | VERIFIED |
| `CapEff`/`CapPrm`/`CapBnd` | `000001ffffffffff` | VERIFIED |
| `/proc/cmdline` | `console=ttynull,115200 rootfstype=squashfs quiet maxcpus=4 rootwait no_console_suspend earlycon=uart8250,mmio32,0xfd099000,baudrate=115200 nvt_pstore_mmc.blkdev=/dev/mmcblk0p36 page_pinner=on page_owner=on root=/dev/mmcblk0p20 ro` | VERIFIED |

## SELinux

| Fact | Value | Label |
| :--- | :--- | :--- |
| `getenforce` | `Enforcing` | VERIFIED |
| `/sys/fs/selinux/enforce` | `1` | VERIFIED |
| `/sys/fs/selinux/policyvers` | `33` | VERIFIED |
| `/sys/fs/selinux/policy` size | `252211` bytes | VERIFIED |
| `/sys/fs/selinux/policy` sha256 | `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2` | VERIFIED |
| Kernel log | `security_sid_to_context_core: called before initial load_policy on unknown SID 59` (repeating) | VERIFIED |
| Effective enforcement | permissive v33 policy loaded; seloff carrier active | INFERRED |

The policy hash matches the after-boot export in
[15-selinux-runtime-control.md](15-selinux-runtime-control.md), so the
permissive v33 policy is the loaded one. The `security_sid_*` errors indicate
`selinux_state.initialized=0`, i.e. the `ndp_logo` seloff carrier is active.

## Filesystem availability (Phase D blocker)

| Fact | Value | Label |
| :--- | :--- | :--- |
| `/proc/filesystems` | no `overlay`, no `btrfs`; has `squashfs`, `ext2/3/4`, `vfat`, `fuse`, `incremental-fs`, `selinuxfs`, `pstore` | VERIFIED |
| overlayfs available | **No** (not built in, module not loaded, no `/lib/modules`) | VERIFIED present-absence |
| `/dev/mem`,`/dev/kmem` | absent | VERIFIED |
| `/proc/kcore`,`/proc/config.gz`,`/proc/kexec*` | absent | VERIFIED |
| `kptr_restrict` | `0` | VERIFIED |
| `dmesg_restrict` | `0` | VERIFIED |
| `/sys/class/backlight` | empty (no entries) | VERIFIED |
| `/sys/class/leds` | empty (no entries) | VERIFIED |

Consequence: the durable-root strategy in use is loop-mounted ext4 + bind
mounts, **not** overlayfs. Any Phase D.2 "overlay" plan must be a bind/loop
plan. See below for the existing implementation.

## Partitions (canonical, live)

`/proc/partitions` reports `mmcblk0` = 7,634,944 KiB and `p1..p40`, plus
`mmcblk0boot0`/`mmcblk0boot1` = 4096 KiB each. Sizes in KiB (selected):
`p9=8192`, `p11=1024`, `p20=30720` (root), `p31=1879040` (apdat),
`p36=2048` (pstore). `sda` = 3,921,919 KiB / `sda1` = 3,919,872 KiB (USB).

Label: VERIFIED. Matches [02](../reference/partition-map.md) and doc 12.

## `/proc/iomem` (hardware map)

| Range | Use | Label |
| :--- | :--- | :--- |
| `0x02800000-0x234fffff` | System RAM; kernel code `0x02810000-0x0391ffff`, data `0x03a80000-0x03cbffff` | VERIFIED |
| `0x32c00000-0x34ffffff`, `0x80000000-0x997fffff`, `0xa0000000-0xbfffffff` | System RAM regions | VERIFIED |
| `0xfc000000.ehci`, `0xfc040000.rtc`, `0xfc048300.mmc`, `0xfc090000 ntkxdma`, `0xfc0c0000 ntkhdma` | peripherals | VERIFIED |
| `0xfd090000/0xfd092000/0xfd099000 serial` | three UART MMIO windows | VERIFIED |
| `0xfd0b0000 imvq-img-dec`, `0xfd020000 imvq-venc`, `0xffe00000.gpu` | media/GPU | VERIFIED |

## Device surface (corrected)

`ntkmem` is **504:0** on this build, not 503:0 as doc 16 states. Full vendor
node set with observed majors:

```
ntkmem 504:0   ndp_hwmem 10:192   ntgpio 132:0     ntkiic0 134:0
ntkled 503:0   ntktcon 242:0      ntkhdmi 241:0     ntkvd 237:0
ntkvplt 238:0  ntkdemod 239:0     ntkdvif 240:0     ntkstbc 244:0
ntkaxis 245:0  ntksys 246:0       ntkgpu 235:0      ntkcal 236:0
ntkci 131:0    ntkconverter 225:0 ntkdispage 234:0  ntkhdma 510:0
ntkxdma 511:0  ntkbm 10:125       ntkgai 10:120     ntkgpu3d 10:122
ktcon_misc 10:121  kadc_misc 10:124  kblast_misc 10:123
ndp_tsmux 66:0 ndpcust 502:0      ndppq 505:0
nvt_atsc30dmx 507:0  nvt_atsc30lmt 506:0  nvt_dvb_demux0..2 508:0..2
teec 501:0     sdp_mem 509:0      nvt_tk_boot_counter 10:127
uinput 10:223  uhid 10:239        gpiochip0 254:0
```

Input: `/proc/bus/input/devices` is **empty**; `/dev/input` holds no device
nodes. Remote keys do not arrive via evdev. VERIFIED.

`/sys/class` includes `backlight`, `leds`, `gpio`, `drm`, `graphics`, `i2c-dev`,
`input`, `mem`, `mtd`, `uio`, `video4linux`, `power_supply`, `thermal`.
`/sys/class/graphics` = `fb0..fb4`.

## New subsystem not in 15/16: OP-TEE

| Fact | Value | Label |
| :--- | :--- | :--- |
| Modules | `tee`, `kteeclient` loaded | VERIFIED |
| Nodes | `/dev/teec` (501:0), `kteeclient` class, `tee` group | VERIFIED |
| Threads | multiple `[teec_service]`, `[teec_kservice]` | VERIFIED |
| Meaning for root | normal-world root does not imply secure-world access | INFERRED |

This is a distinct trust boundary from SELinux; treat secure-world as
**UNKNOWN / out of scope** until separately probed.

## dm-verity is active

`ps` shows `[kverityd]` (×5) and `[kdmflush/253:*]`; `/dev` has `dm-0..9`,
`nfsb-2..5`, `linear-2..5`. Matches doc 17's verifier description. Label:
VERIFIED presence; per-target verity parameters `UNKNOWN`.

## Modules

42 vendor modules; `Tainted: P`. `ndp_logo 24576 0 Live`. `modules_disabled=0`.
`/sys/module/ndp_logo/parameters` is empty (no `logomajor` side channel on the
currently loaded instance). The seloff `.ko` files exist on `apdat` (below).

## Tooling availability (on-device, PATH)

| Present | Absent |
| :--- | :--- |
| `ldd`, `wget`, `iptables`, `ip6tables`, `nslookup`, `sha256sum` | `gcc`, `cc`, `python`, `python3`, `perl`, `strace`, `ltrace`, `gdbserver`, `curl`, `socat`, `sqlite3`, `ffmpeg`, `objdump`, `readelf`, `nc` |

Caveat: some "absent" tools exist as files not on `PATH`:
`/mtd_apexe/board/curl`, `/mtd_apexe/board/sqlite3`, `/mtd_apexe/board/iperf`,
`/mtd_rwarea/apdat/busybox`. Invoke by absolute path; do not assume PATH.

## Listener audit (ports only; addresses redacted)

Wildcard listeners include `2323` (telnetd), `7788` (webview CDP), `8009`,
`8002`, `7000`, `8883`, `4123`, `49152`, `12345`, `26441-26444`,
`56789`,`56790`. Loopback-only: `8080`, `8083`, `9090`, `4040`, `29785`,
`29577`, `11883`. `2323` is bound dual-stack (`::`) via busybox telnetd.

Process mapping (selected): `busybox telnetd` from **`/tmp/persist`** (PID
1146, ephemeral); `apdat/busybox httpd` (PID 573, durable); `com.nvt.opera`
webview (1297) with `omi_worker` children; `idtv` (888); `appmgr` (788).

## Persistence and drift (material)

The device is **far past** the documented root/persist state. On
`/mtd_rwarea/apdat`:

| Artifact | Size | Meaning |
| :--- | ---: | :--- |
| `customer_env.sh` | 3513 B | active hook (docs describe 263–914 B versions) |
| `customer_env.sh.bak-*` | many | at least 12 distinct backups through 20261105 |
| `root_boot.sh` / `root_boot.log` / `root_boot.ready` | 3194 / 175064 / 53 B | supervisor + log |
| `busybox` | 1,284,688 B | durable busybox |
| `policy.33.perm.bin` | 252,211 B | permissive v33 policy |
| `ndp_logo_boot.ko`, `ndp_logo_seloff_boot.ko` | 38,976 B each | no-op and seloff carriers |
| `custom.sqsh` | 4,096 B | custom squashfs stub |
| `offlinelauncher.stock.tar` | 5,253,120 B | launcher backup |
| `ui-page.stock.tar` | 154,787,840 B | UI backup |
| `apexe_ext0.backup`,`apexe_ext1.backup` | 576,716,800 B each | partition backups |
| `freetitan-*.sh/.on/.log` | 0.9–121 KB | custom-root supervisor set |

Mounted custom rootfs (live `/proc/mounts`):

```
/dev/loop6 /tmp/freetitan-root            squashfs ro
/dev/loop5 /tmp/freetitan-data            ext4 rw
bind: loop5 -> /tmp/freetitan-root/{etc,var,home,root,opt,usr/local}
bind: /dev/root -> .../{bin,lib,sbin,usr}  squashfs ro
```

`/swdl` (rw) holds `autorun.upg` (917,372,175 B), `boot0.bin` (4,194,304 B),
`boot0.b64`, `policy33.bin` (294,139 B), `mount.copy`, `umount.copy`.

Label: VERIFIED presence. This is the "separate private OS project" the
README says lives elsewhere; it is now live on this unit and contradicts the
public-scope statement. Flagged, not resolved.

## Discrepancies against published docs (do not silently upgrade)

| Doc | Published | Live | Action |
| :--- | :--- | :--- | :--- |
| 16 | `ntkmem` 503:0 | `ntkmem` 504:0 | correct doc 16 |
| 16 | node list | missing `teec`, `sdp_mem`, `nvt_tk_boot_counter`, `ndp_tsmux`, `ndpcust`, `ndppq`, `ntkxdma`, `ntkhdma` | extend doc 16 |
| 16 | no TEE | OP-TEE present (`teec`, `kteeclient`) | new DOC/OPEN |
| 12/16 | seloff via `logomajor` side channel | `ndp_logo` params empty | re-verify carrier variant |
| README | "public repo stops at research and root" | freetitan custom rootfs live | state-scope mismatch |
| README | root context `initrc_t` | `id` printed no context (seloff) | clarify |

## Open / UNKNOWN (Phase A did not answer)

- `/dev/ntkmem` (504:0) and `/dev/ndp_hwmem` (10:192): do they mmap arbitrary
  physical ranges or only allocator/CMA nodes? UNKNOWN. Needs a Phase B harness.
- ioctl request numbers, struct layouts, and semantics for every `ntk*` node:
  UNKNOWN. Must be measured, never guessed.
- `ntkled`/`ntktcon` control path: no `backlight`/`leds` sysfs on-ramp exists,
  so panel/backlight must go through these ioctls. UNKNOWN ABI.
- Secure world (OP-TEE) capabilities and whether it gates any of the above:
  UNKNOWN.
- dm-verity target parameters per `dm-2..9` / `nfsb-*`: UNKNOWN.
- Whether `modprobe overlay` could ever work (no module source on device):
  UNKNOWN, treated as unavailable for planning.

## Safety

- Phase A only: no `mknod`, `insmod`, `/dev` writes, `/sys` writes, or
  partition access. The single follow-up connection ran only `ls`/`cat`.
- Recovery for any later phase remains a cold boot plus the `apdat` hook
  backups listed above.
