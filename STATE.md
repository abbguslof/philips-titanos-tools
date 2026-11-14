# Current state

Updated: 2026-11-15.

Target: Philips `55PUS8000/12`, chassis `TPA256E` / `TPN256E`, mainboard
`715GD542`, firmware `TPA256E_V056.002.236.191`.

This page is the short source of truth for the live lab unit. The research
documents hold the evidence; this page records what is true now and what is
blocked.

Status labels: **VERIFIED**, **REPORTED**, **TESTED-NEGATIVE**, **INFERRED**,
**OPEN**.

## Verified

| Area | State | Evidence |
| :--- | :--- | :--- |
| Root | `uid=0` on TCP `:2323` after a USB cold boot | [USB autoroot](docs/research/05-usb-autorun-hook.md) |
| Persistence | `customer_env.sh` hook survives a USB-less cold boot | [Persistence](docs/research/06-persistence-customer-env.md) |
| SSH | Key-only Dropbear on `:2222` after a USB-less cold boot | [Dropbear](docs/research/23-dropbear-ssh-2026-11-10.md) |
| SELinux | `Enforcing`; policy version 33; loaded policy sha256 `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`; permissive v33 policy active; `ndp_logo` seloff carrier loaded | [SELinux](docs/research/15-selinux-runtime-control.md), [kernel](docs/research/16-kernel-and-hardware-control.md) |
| Kernel | `6.1.124-gd063554eebf5-ab6`; `modules_disabled=0`; unsigned vendor modules load | [Live inventory](docs/research/18-live-inventory-2026-11-09.md) |
| Boot hooks | `run.sh:461` sources `customer_env.sh`; `run_custom_impl.sh:133` runs `/swdl/telnet/telnetd` | [Persistence](docs/research/06-persistence-customer-env.md), [`/swdl` variant](docs/research/24-swdl-telnet-persistence-2026-11-11.md) |
| Boot areas | 4 MiB, `force_ro=1`, `ro=1`. Active boot0 `1c74949e…`; recovery boot1 `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd`. The vendor update wrote boot0; boot1 is the pre-update recovery | [Vendor update](evidence/deep/2026-11-14-ndal-v4l2-reset.md) |
| Boot map | `p1`/`p2` UMFG slots; `p9` slot map; `p13`/`p14` ATF; `p15`/`p16` FDT; `p17`/`p18` kernel; `p19`/`p20` rootfs; `p21` plain `kerupm` | [Boot image map](docs/research/28-boot-image-map.md) |
| Recovery backup | Full `mmcblk0` image and boot areas; `sha256sum -c` passes | [2026-11-14 backup](evidence/deep/2026-11-14-emmc-backup.md) |
| Restore | Same-byte write to both boot areas, read-back hashes, and cold boots verified | [2026-11-14 backup](evidence/deep/2026-11-14-emmc-backup.md) |
| Update package | `sys_run`/`kerupm`/`eburner` map; `kerupm` matches `p21`; burner checks are MD5-only | [Update path](docs/research/30-update-path-2026-11-14.md) |
| App-layer update gate | **VERIFIED on hardware.** The genuine VER40 USB package loaded, validated, and programmed active slot 0 (`p15`/`p17`/`p19`); AC-on activated it. Version `002.236.191`; root and persistence survived. Old slot 1/boot1 is the recovery pair. The RSA gate remains the barrier for modified packages | [App-layer gate](docs/research/31-app-update-gate-2026-11-14.md) |
| NDAL V4L2 reset | `NDAL_VideoExt_STBC_ResetByHWWDT_*` uses control `0x0f170f1f`/`0x0f170f29` (class `0x0f170000`), ioctl `0xc0185647`, 20-byte controls, and `/dev/video24`. The classic eburner initramfs uses a USB image (`/media/sda1/nvt_tv_firmware.img`), not `/swdl`; the p9 metadata layout (`PPCH`/`FWVR`/`UPST`/`BTFG`) is mapped. The entry trigger remains open | [NDAL V4L2](docs/research/32-ndal-v4l2-reset-2026-11-14.md) |
| `/swdl` and p9 | Vendor `/swdl/autorun.upg` `74d2790a…`; p9 `7e8fca3d…` (post-update); active boot0 `1c7494…`/slot 0 `002.236.191`; recovery boot1 `eee415…`/slot 1 `002.235.191`; STBC off | [NDAL evidence](evidence/deep/2026-11-14-ndal-v4l2-reset.md) |
| Runtime NFSB | Inner SquashFS mounts read-only at offset `0x1000` | [Runtime NFSB](docs/research/17-runtime-nfsb-squashfs.md) |

## Live drift

The public repo documents research and root. The live unit is further along:

- `/root` is a 700 tmpfs; `/etc/profile.d` is bind-mounted from `apdat`.
- `/mtd_rwarea/apdat` holds `customer_env.sh` (3513 B), `root_boot.sh`,
  `busybox`, `policy.33.perm.bin`, `ndp_logo_boot.ko`,
  `ndp_logo_seloff_boot.ko`, `opt/`, and the persistent-root scripts and logs.
- `/swdl` holds `autorun.upg` (917,372,175 B), `autorun_size.txt`, and
  `autorun_version.txt`.
- The vendor VER40 USB update wrote active slot 0 (`p15`/`p17`/`p19`) and
  boot0; AC-on activated it. Firmware `002.236.191`; recovery slot 1/boot1 is
  the previous `002.235.191`. Root and persistence survived.
- The earlier 2026-11-14 eburner retries restored the vendor
  `/swdl/autorun.upg`, the p9 `misc`, and the STBC mode. Those boot areas are
  now the recovery pair.
- The private custom userspace is outside this repository's public scope. This
  page records the root hook, not its internals.

## Open gates

- [x] Full eMMC and boot-area backup (2026-11-14).
- [x] Same-byte restore test: wrote the stock bytes back to `mmcblk0boot0` and
  `mmcblk0boot1`, read back the hashes, restored `force_ro`, and cold-booted
  both times. See [backup evidence](evidence/deep/2026-11-14-emmc-backup.md).
- [ ] Corrupted-image restore: prove recovery from a deliberately corrupted
  boot area. The vendor update wrote known-good boot0; boot1 is the recovery.
  The eMMC boot-area selection/ISP/JTAG path is still untested.
- [x] App-layer USB update trigger: USB package -> `/swdl/autorun.upg` ->
  verify -> eburner flag -> reset. See
  [app-layer gate](docs/research/31-app-update-gate-2026-11-14.md).
- [x] Vendor VER40 USB update: the genuine package loaded, validated, and
  programmed active slot 0 (`p15`/`p17`/`p19`); AC-on activation; version
  `002.236.191`; root/persistence survived.
- [x] A/B recovery pair: active boot0/slot 0 new; recovery boot1/slot 1 old.
  The eMMC boot part (`nvt_emmc_set_boot_part_id` `0xa679`) and the p9
  `NVHC`/`bflag` are available; the pair switch is not yet exercised.
- [x] Eburner flag path: `PKG_ready<path>` at `misc + 0x3e00`, STBC ioctl
  `0xc0105310`, and a no-op status function. See
  [app-layer gate](docs/research/31-app-update-gate-2026-11-14.md).
- [x] Eburner trigger (historical): the STBC eburner mode + `PKG_ready` + AC
  entered the eburner twice and consumed the classic package; a paused-appmgr
  retry kept the package but did not enter. The trigger is not repeatable.
- [x] NDAL V4L2 reset helper: the control id/layout, `libv4l2` provider, and
  `/dev/video24` are resolved. A local dynamic helper calls
  `NDAL_VideoExt_OpenDevice(0, 0xA)` and
  `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn`; the wrapper resets the TV.
- [ ] Eburner entry with the USB image and p9 metadata: the classic initramfs
  reads `/media/sda1/nvt_tv_firmware.img` (or `nvt_eburner_img=`), extracts
  `sys_run`, and runs `/tmp/sys_run/run.sh`. The full classic package on the
  USB and the p9 metadata (`UPST` `0x3600`, `BTFG` `0x3800`, `PKG_ready`
  `0x3e00`) did not produce the script. The bootloader/boot flag is open; the
  extraction path is mapped.
- [ ] App-layer modified package: patch `libfwup` RSA
  (`nvtfw_sec_verify_whole_img_sign` `0xb889` or `nvtfw_enable_secure_boot`
  `0x6d3d`) and the app-layer version check; build a modified VER40 component;
  keep the old pair as recovery.
- [x] `kerupm` package/live match: plain uImage, valid data CRC, exact bytes at
  `p21`. Update-mode selection is open.
- [ ] `p1`/`p2` FIT and `VTBL`/`NVHC` verifier map. The `p9` `PPCH` slot map is
  decoded; the live `VTBL`/`STBC` differ from the package.
- [ ] Generalize the kernel carrier.
- [x] A/B recovery pair exists (slot 0/boot0 new; slot 1/boot1 old); the pair
  switch is not yet exercised.

## Next action

1. Keep a second copy of the 2026-11-14 backup off the TV.
2. Exercise the A/B recovery pair switch (eMMC boot part plus p9 slot) before
   any modified boot-area write. The vendor update wrote active boot0/slot 0;
   recovery boot1/slot 1 is the old version.
3. Patch `libfwup` RSA (`nvtfw_sec_verify_whole_img_sign` `0xb889` or
   `nvtfw_enable_secure_boot` `0x6d3d`) and the app-layer version check. Build
   a modified VER40 package, starting with a harmless component, and keep the
   old pair recovery.
4. The classic eburner USB entry remains open. The serial console is the
   diagnostic if that route continues. See
   [NDAL V4L2](docs/research/32-ndal-v4l2-reset-2026-11-14.md).
5. The corrupted-image restore is still the gate for modified boot-area
   writes. See [recovery gate](docs/guides/recovery-gate.md).

## Stop conditions

- No full backup.
- No verified restore of a deliberately corrupted boot area.
- No way to select or recover the boot area.
- Field units (`TPN236E`, `TPN258E`, `TPN256E` variants): read-only only.

## Links

- [Recovery gate](docs/guides/recovery-gate.md)
- [Deep jailbreak roadmap](docs/research/25-deep-jailbreak-roadmap.md)
- [Recovery engineering](docs/research/26-recovery-engineering.md)
- [Boot image map](docs/research/28-boot-image-map.md)
- [Update package map](docs/research/29-update-package-map.md)
- [Update path](docs/research/30-update-path-2026-11-14.md)
- [App-layer update gate](docs/research/31-app-update-gate-2026-11-14.md)
- [NDAL V4L2 reset](docs/research/32-ndal-v4l2-reset-2026-11-14.md)
- [43PUS7608/12 field scan](docs/research/34-tpn236e-43pus7608-2026-11-14.md)
- [2026-11-14 backup evidence](evidence/deep/2026-11-14-emmc-backup.md)
- [2026-11-14 NDAL evidence](evidence/deep/2026-11-14-ndal-v4l2-reset.md)
