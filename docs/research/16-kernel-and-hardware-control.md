# Kernel, module, and hardware control surfaces

Status: **VERIFIED / OPEN** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-01. No boot-chain or partition writes.

## Why this matters

The permissive v33 policy removed the SELinux blocker for userspace and
`mounton`. The remaining control wall is the kernel and the closed boot chain.
This page records what is reachable from the live root shell without touching
the boot chain.

## Loadable modules are available

`/proc/modules` lists 42 vendor modules, and the matching `.ko` files are on the
read-only app partition:

```text
/mtd_apexe/board/modules/*.ko
```

Key facts:

```text
/proc/sys/kernel/modules_disabled  0
insmod /sbin/insmod                present
modprobe /sbin/modprobe            present
/lib/modules, /usr/lib/modules     absent
vermagic                           6.1.124-gd063554eebf5-ab6 SMP preempt mod_unload modversions aarch64
module signatures                  none observed in vendor .ko files
```

The kernel accepts unsigned vendor modules. A live test loaded
`ndp_nvtmem.ko` and removed it cleanly:

```text
insmod /mtd_apexe/board/modules/ndp_nvtmem.ko   # rc=0
/dev/ntkmem_ramtest                             # 10:117
rmmod ndp_nvtmem                                # rc=0
```

`ndp_nvtmem` is a RAM-test helper: it allocates pages and maps a fixed physical
range for testing. It is not an arbitrary kernel-memory window. It was unloaded
after the probe.

## Building a custom module

There are no kernel headers, build tree, `/proc/config.gz`, BTF, or
`Module.symvers` on the TV. The modules were built with Android Clang 17 and
`CONFIG_MODVERSIONS`. A custom module therefore needs one of:

1. Exact vendor kernel source/config and `Module.symvers`; or
2. A vendor `.ko` used as a carrier, with its init/cleanup code patched; the
   carrier keeps the correct `.modinfo`, `__versions`, relocations, and
   `this_module` layout.

The carrier route is the practical next probe. First make a benign
return-only module, load/unload it, then add a minimal payload. This would give
kernel code execution but is a kernel-level change with crash risk; keep the
root hook and a cold-boot recovery.

### Carrier proof (2026-11-01)

`ndp_logo.ko` (38,976 bytes, no dependencies) was copied to `/tmp`, its
`init_module` and `cleanup_module` entry points were patched to
`mov w0,#0; ret`, and the module was loaded:

```text
insmod /tmp/ndp_logo_test.ko   # rc=0
ndp_logo 24576 0 - Live       # /proc/modules
rmmod ndp_logo                # rc=0
```

This proves arbitrary unsigned code can run in kernel context. The patch did
not create a device or touch hardware.

### Corrected carrier and kernel read/write proof

The first payload attempt placed code at `.init.text+4`, which overlaps
`R_AARCH64_*` relocations at `0x10`, `0x20`, `0x28`, and `0x2c`. The loader
patched over the payload; `insmod` segfaulted, the module stuck in `Loading`,
`rmmod -f` was busy, and `reboot` hung. A cold power cycle cleared it. The
permissive policy and root hook survived.

The corrected payload works:

1. Entry (`init_module+4`) saves `x20`, branches to the relocated `adrp` at
   `.init.text+0x10`, then branches to the relocation-free tail at `0x640`
   (last relocation is `0x630`).
2. The relocated `adrp x20` supplies the page of `.bss+8`; `add x20,x20,#8`
   addresses `logomajor` without hardcoding the module base.
3. Set `__param_logomajor` permission to `0444`, making
   `/sys/module/ndp_logo/parameters/logomajor` a readable side channel.
4. The payload reads `selinux_state` and stores the word in `logomajor`; `x20`
   is restored before return.

Dump of offset 0:

```text
logomajor = 16843008 = 0x01010100
bytes     = 00 01 01 01
```

This fits `CONFIG_SECURITY_SELINUX_DEVELOP=n`: `checkreqprot=0`,
`initialized=1`, then policy-capability bits. A write to `selinux_state+1=0`
changed the word to `16842752 = 0x01010000`, proving arbitrary kernel write.
`getenforce` still read `Enforcing`, but the kernel logged:

```text
SELinux: security_sid_to_context_core: called before initial load_policy ...
audit: error in audit_log_exit()
```

That state is not stable and was restored by writing `1` back to
`selinux_state+1`; a cold reboot returned the clean permissive state. Do not
persist `initialized=0`; the permissive policy is the stable effective-off
state.

The no-op carrier was first persisted as a safe boot scaffold:

```text
/mtd_rwarea/apdat/ndp_logo_boot.ko      38,976 bytes
sha256                                  fbc4ae3fb26970edee928b66eee3a548bc924a75461fc1f30c577e1aba68a749
backup                                  customer_env.sh.bak-before-kernel-boot-20261101
```

It loaded on cold boot with no side effect. The scaffold was then replaced by
the seloff payload.

### Persistent seloff payload

The one-shot boot test of `selinux_state.initialized=0` succeeded: the TV
booted, `appmgr`/`idtv`/browsers started, and the root shell came up. It was
then made persistent:

```text
/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko   38,976 bytes
sha256                                      cacfcd82d103c5a0c2e0c4055e4452aaf96c2e275ce41d2b124f9ed86588047e
customer_env hook                           insmod after the policy load
kill switch                                 create /mtd_rwarea/apdat/no_kernel_module to skip
backup                                      customer_env.sh.bak-before-seloff-persist-20261101
```

Two cold boots verified it. Result:

```text
ndp_logo                   Live
getenforce                 Enforcing
permissive policy hash     b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2
appmgr/idtv/browser        running
dmesg                      security_sid_to_context_core: called before initial load_policy
```

The kernel still reports `Enforcing` because the global flag is separate. The
payload clears `selinux_state.initialized`, so SELinux hooks treat the policy as
not loaded. The audit/context log errors are expected and noisy; no crash or
boot failure was observed. This is not a clean `selinux=0`; the stable fallback
is the permissive v33 policy.

### Rollback

Create `/mtd_rwarea/apdat/no_kernel_module` and cold boot, or restore
`customer_env.sh.bak-before-seloff-persist-20261101`. The seloff module file can
remain on `/mtd_rwarea`; it is inert without the hook.

## Direct kernel access is still closed

- `/dev/mem` and `/dev/kmem` are absent; `mknod` succeeds but `open()` returns
  `No such device or address`.
- `/proc/kcore`, `/proc/config.gz`, `/sys/kernel/btf/vmlinux`, and `/proc/kexec*`
  are absent.
- `/sys/fs/selinux/disable` exists but writing `1` returns `EINVAL`.
- `kallsyms_lookup_name` is `T`, but not exported. `selinux_state` is
  `ffffffc0093caaf0 B`; the global enforcing flag is not directly writable.
- `selinux_state` is `__randomize_layout`; do not guess field offsets.

## Hardware device surface

Root already has many vendor character devices. Permissions are root/nvtdrv,
not world-readable, but the root shell can use them:

```text
/dev/ntkmem            503:0      world-writable; ndp_misc KER_MEM_IOCtl
/dev/ndp_hwmem         10:192     hardware memory/DMA users
/dev/ntgpio            132:0
/dev/ntkiic0           134:0
/dev/i2c-0..5          89:0..5
/dev/ntkled
/dev/ntktcon
/dev/ntkci
/dev/ntktspu, ntktspu1, ntktspu2
/dev/ntkhdmi
/dev/ntkdvif, ntkdemod, ntkvd
/dev/ntkbm, ntkcal, ntkconverter, ntkdvif, ntkdispage
/dev/fusion0..31
/dev/dri/*
/dev/fb0..4
/dev/mmcblk0boot0, mmcblk0boot1
/dev/uinput, /dev/uhid
```

This is a real hardware-control layer for panel, backlight, HDMI, tuner,
Ambilight, audio, and input. The ioctls are undocumented; each driver needs its
own static reverse engineering. Do not write boot partitions.

## Input path

- `/dev/uinput` and `/dev/uhid` exist; virtual input injection is possible.
- `/proc/bus/input/devices` is empty and `/dev/input` only has `mice`.
- Remote keys arrive through the Novatek input driver and `idtv`/`appmgr`, not
  standard evdev.
- `nvt.app.ini` has `hotkey` entries (`f1=primevideo`, `f2=netflix`,
  `f3=demo1`); the appmgr data seam can override them.
- Full remap of the dedicated Netflix/Prime/Disney/YouTube/Viaplay buttons
  still needs the proprietary key path or a custom native helper.

## Boot chain

No new bootarg route was found:

- NVM p9 has no `bootargs`.
- `mmcblk0boot0`, vendor `p1`/`p2`, `uboot_payload.bin`, and `frcfw.bin` do not
  contain the live `console=ttynull`/`root=` command line.
- The live command line is in the FDT/ATF path. `selinux=0`/`enforcing=0`
  remains a boot-chain write with no proven unbrick.

## Ranked next probes

1. **Audit `/dev/ntkmem` and `/dev/ndp_hwmem`.** Determine whether either can
   mmap an arbitrary physical range or only allocator/CMA nodes. If arbitrary,
   kernel memory becomes reachable without a custom module.
2. **Carrier module proof.** Patch an unloaded vendor `.ko` (e.g. `ndp_logo` or
   `8192fu`) init/cleanup to return safely; load/unload. Then add a minimal
   kernel payload. Do this with the root hook and cold-boot recovery ready.
3. **Input remap.** Use `uinput` for local input, map `nvt.app.ini` hotkeys, and
   trace the proprietary remote key path before touching dedicated buttons.
4. **Hardware drivers.** Reverse engineer the specific `/dev/ntk*` ioctl needed
   for the feature (backlight, HDMI, Ambilight, tuner), one device at a time.
5. **Do not** write `mmcblk0boot*` or NFSB boot images without an ISP/vendor
   recovery path.

## Safety

- No boot-chain, eMMC, or partition writes in this investigation.
- `ndp_nvtmem` was loaded and unloaded cleanly; it is not persistent.
- A custom module can panic or hang the kernel. Every attempt needs a cold-boot
  recovery and one change at a time.
