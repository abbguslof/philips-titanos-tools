# Current state

Updated: 2026-11-22.

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
| Kernel carrier | **VERIFIED on hardware.** The `ndp_logo` carrier loads, exposes the `carrier` parameter, passes the live KCFI set/get check, writes/reads its scratch buffer, resolves symbols, and reads live kernel symbols. Rollback and reboot restored the seloff path | [Level 3.5 carrier](docs/research/37-kernel-carrier-level-3-5.md) |
| Runtime verifier patch | **VERIFIED on hardware.** The carrier calls `nfsb_verify` on a scratch header: pristine returns 0, a modified signature returns `0xffffbf00`, and the two-instruction patch returns 0. Reboot restores `0xd10343fff800865e` | [Runtime verifier patch](docs/research/38-runtime-verifier-patch-2026-11-20.md) |
| Backlight | **VERIFIED on hardware.** `KER_LED_PWM_HWFR_Get/Set_Duty` on `/dev/ntkled`: channel 0 duty `20000`/offset `105`, dim to `10000`, restore; reboot returns the default | [ndp_led backlight](docs/research/39-ndp-led-pwm-backlight-2026-11-20.md) |
| NFSB mount-path check | **VERIFIED on hardware.** `nvt_dm_check_nfsb` rejected a modified loop copy unpatched and accepted it after the `nfsb_verify` patch (`NFSB header found and verified`) | [NFSB mount check](docs/research/40-nfsb-mount-check-2026-11-20.md) |
| NFSB dm mapping | **VERIFIED on hardware.** `nvt_dm_setup_linear` builds the data-area `linear` target and `nvt_dm_setup_nfsb` builds the `verity` target; a read-only loop copy mounted the stock SquashFS. Big-endian header fields `0x06`/`0x0a`/`0x12`/`0x16`/`0x2a` and ASCII `0x1a`/`0x2e`/`0x6f` map to the target params | [NFSB dm mapping](docs/research/43-nfsb-dm-mapping-2026-11-22.md) |
| dm-verity data path | **VERIFIED on hardware.** A modified data block reads through the verity device after the tree is recomputed and the header root digest at `0x6f` is replaced; the stock tree/digest still returns EIO (`data block 100 is corrupted`) | [dm-verity data path](docs/research/44-nfsb-verity-data-path-2026-11-22.md) |
| Custom NFSB image | **VERIFIED on hardware.** A host-built SquashFS + NFSB header/tree (1 MiB data, two-level tree) mounts read-only through `nvt_dm_setup_linear` + `nvt_dm_setup_nfsb`; `hello.txt` and a marker read back. The one-block case is explained (dm-verity zero levels, root `H(salt\|\|data)`) | [Custom NFSB mount](docs/research/45-custom-nfsb-mount-2026-11-22.md) |
| Boot hooks | `run.sh:461` sources `customer_env.sh`; `run_custom_impl.sh:133` runs `/swdl/telnet/telnetd` | [Persistence](docs/research/06-persistence-customer-env.md), [`/swdl` variant](docs/research/24-swdl-telnet-persistence-2026-11-11.md) |
| Boot areas | 4 MiB, `force_ro=1`, `ro=1`. Active boot0 `1c74949e…`; recovery boot1 `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd`. The vendor update wrote boot0; boot1 is the pre-update recovery | [Vendor update](evidence/deep/2026-11-14-ndal-v4l2-reset.md) |
| Boot map | `p1`/`p2` UMFG slots; `p9` slot map; `p13`/`p14` ATF; `p15`/`p16` FDT; `p17`/`p18` kernel; `p19`/`p20` rootfs; `p21` plain `kerupm` | [Boot image map](docs/research/28-boot-image-map.md) |
| Recovery backup | Full `mmcblk0` image and boot areas; `sha256sum -c` passes | [2026-11-14 backup](evidence/deep/2026-11-14-emmc-backup.md) |
| Restore | Same-byte write to both boot areas, read-back hashes, and cold boots verified | [2026-11-14 backup](evidence/deep/2026-11-14-emmc-backup.md) |
| Update package | `sys_run`/`kerupm`/`eburner` map; `kerupm` matches `p21`; burner checks are MD5-only | [Update path](docs/research/30-update-path-2026-11-14.md) |
| App-layer update gate | **VERIFIED on hardware.** The genuine VER40 USB package wrote slot 0/boot0 (`p15`/`p17`/`p19`). The live boot stayed slot 1/boot1 (XBoot `2a4184c`, p20 rootfs, p9 DBFG 2, `lnikauth pass`). Slot 0 fails `lnikauth`; the A/B switch to it is TESTED-NEGATIVE. Root and persistence ran on slot 1. The RSA gate remains the barrier for modified packages | [App-layer gate](docs/research/31-app-update-gate-2026-11-14.md), [A/B failure](docs/research/48-ab-switch-failure-2026-11-22.md) |
| NDAL V4L2 reset | `NDAL_VideoExt_STBC_ResetByHWWDT_*` uses control `0x0f170f1f`/`0x0f170f29` (class `0x0f170000`), ioctl `0xc0185647`, 20-byte controls, and `/dev/video24`. The classic eburner initramfs uses a USB image (`/media/sda1/nvt_tv_firmware.img`), not `/swdl`; the p9 metadata layout (`PPCH`/`FWVR`/`UPST`/`BTFG`) is mapped. The entry trigger remains open | [NDAL V4L2](docs/research/32-ndal-v4l2-reset-2026-11-14.md) |
| `/swdl` and p9 | Vendor `/swdl/autorun.upg` `74d2790a…`; p9 `7e8fca3d…` (post-update); the update wrote boot0 `1c7494…`/slot 0 (p19 new rootfs); the live boot was boot1 `eee415…`/slot 1 (p20 old rootfs) with p9 DBFG 2; STBC off; slot 0 fails `lnikauth` | [NDAL evidence](evidence/deep/2026-11-14-ndal-v4l2-reset.md), [A/B failure](docs/research/48-ab-switch-failure-2026-11-22.md) |
| Runtime NFSB | Inner SquashFS mounts read-only at offset `0x1000` | [Runtime NFSB](docs/research/17-runtime-nfsb-squashfs.md) |

## Live drift

The public repo documents research and root. The live unit is further along:

- `/root` is a 700 tmpfs; `/etc/profile.d` is bind-mounted from `apdat`.
- `/mtd_rwarea/apdat` holds `customer_env.sh` (3513 B), `root_boot.sh`,
  `busybox`, `policy.33.perm.bin`, `ndp_logo_boot.ko`,
  `ndp_logo_seloff_boot.ko`, `opt/`, and the persistent-root scripts and logs.
- `/swdl` holds `autorun.upg` (917,372,175 B), `autorun_size.txt`, and
  `autorun_version.txt`.
- The vendor VER40 USB update wrote slot 0 (`p15`/`p17`/`p19`) and boot0. The
  live boot stayed slot 1/boot1 (p20/old), XBoot `2a4184c`, p9 DBFG 2,
  `lnikauth pass`. The p9 version is `002.236.191`; the live rootfs was slot 1.
  Root and persistence ran on slot 1. The update slot 0 fails `lnikauth`.
- The earlier 2026-11-14 eburner retries restored the vendor
  `/swdl/autorun.upg`, the p9 `misc`, and the STBC mode. Those boot areas are
  now the recovery pair.
- The private custom userspace is outside this repository's public scope. This
  page records the root hook, not its internals.

## External field units

These are external reports, not maintainer reproductions. Do not apply the lab
bootchain or kernel carrier to them.

| Unit | State | Evidence |
| :--- | :--- | :--- |
| `43PUS7608/12` (`TPN236E`, `236.006.169.001`) | **REPORTED (root).** The USB flag `nbrowser_log_to_file` opens CDP on `:7788`; the launcher RPC bridge injects a shell command as `idtv`; `customer_env.sh` grants root on reboot. Two stick boots and one stick-free boot. Physical only. | [RPC-injection root](docs/research/42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md) |
| `55PUS8108/12` (`TPN236E`, `236.006.169.001`) | **REPORTED.** Boot record (`rcS`, UID 0, `initrc_t`), a fixed UID 0 command across two separately prepared sessions, and an owner-built ARM probe on hardware. Interactive root, unattended persistence and restore open. | [Field report](docs/research/41-tpn236e-55pus8108-2026-11-21.md) |
| `50PUS8909/12` (`TPN248E`, `TPN248E_V248.010.000.121`) | **REPORTED / OPEN.** JointSpace 6.1; USB autoroot failed; offline `ttyS0` getty and empty root password in the 2025 image; installed 2026 build untested. | [Field report](https://github.com/abbguslof/philips-titanos-tools/issues/10) |
| `55PML9019/12` (`TPN248E`, `248.010.000.121`) | **REPORTED (control only).** JointSpace 6.1; Titan OS MQTT, DIAL, Wake-on-LAN; Nagra DRM; root untested. | [Titan OS control report](docs/research/47-titanos-control-field-reports-2026-11-22.md) |
| `77OLED759/12` | **REPORTED (control only).** JointSpace 6.1.0; HTTPS/Digest pairing; direct keys; root untested. | [Titan OS control report](docs/research/47-titanos-control-field-reports-2026-11-22.md) |

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
- [x] Vendor VER40 USB update: the genuine package wrote slot 0
  (`p15`/`p17`/`p19`); the live boot stayed slot 1/boot1 with `lnikauth pass`;
  root and persistence ran on slot 1. The p9 version is `002.236.191`.
- [x] A/B switch: **TESTED-NEGATIVE.** Slot 0 fails `lnikauth`; the p9 DBFG
  selects the pair (`bc:2` slot 1, `bc:1` slot 0). The old slot 1/boot1 is the
  licensed pair. See [A/B failure](docs/research/48-ab-switch-failure-2026-11-22.md).
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
- [x] Reusable kernel carrier. Host build/control tooling, live load, KCFI
  set/get, self-buffer write/read, symbol resolution, and safe reads are
  verified on the lab (2026-11-20); rollback and reboot restored the seloff
  path. See [Level 3.5 carrier](docs/research/37-kernel-carrier-level-3-5.md).
- [x] First Level 3.5 payload: direct `nfsb_verify` patch. The carrier holds a
  real header, rejects a modified signature, and accepts it after the
  two-instruction patch; reboot restores the original. See
  [Runtime verifier patch](docs/research/38-runtime-verifier-patch-2026-11-20.md).
- [x] NFSB mount-path check: `nvt_dm_check_nfsb` rejected a modified loop copy
  unpatched and accepted it after the patch (`NFSB header found and verified`).
  See [NFSB mount check](docs/research/40-nfsb-mount-check-2026-11-20.md).
- [x] ndp_led PWM backlight: channel 0 duty dimmed and restored; reboot returns
  the default. See
  [ndp_led backlight](docs/research/39-ndp-led-pwm-backlight-2026-11-20.md).
- [x] Full `nvt_dm_setup_nfsb` dm mapping: `nvt_dm_setup_linear` and
  `nvt_dm_setup_nfsb` build the `linear` and `verity` targets; a read-only loop
  copy mounted the stock SquashFS. See
  [NFSB dm mapping](docs/research/43-nfsb-dm-mapping-2026-11-22.md).
- [x] dm-verity data path: a modified data block verifies after a recomputed
  tree and header root digest; the stock tree/digest still returns EIO. See
  [dm-verity data path](docs/research/44-nfsb-verity-data-path-2026-11-22.md).
- [x] Custom NFSB image: a host-built SquashFS + header/tree mounts read-only
  through the runtime setup. See
  [Custom NFSB mount](docs/research/45-custom-nfsb-mount-2026-11-22.md).
- [x] Level 4 boot-chain map (read-only): the A/B pair, the static
  VTBL/NVHC/U-Boot slots, the encrypted XBoot pair, the component trailers, and
  the eMMC boot-part switch are mapped. See
  [Level 4 map](docs/research/46-level4-boot-chain-map-2026-11-22.md).
- [x] A/B switch to slot 0: **TESTED-NEGATIVE.** The XBoot prints
  `lnikauth fail`, hits `BC over limit`, and the OBR cannot toggle. The old
  slot 1/boot1 is the licensed pair. The recovery is p9 DBFG 2 and
  `EXT_CSD 0x50`. See
  [A/B failure](docs/research/48-ab-switch-failure-2026-11-22.md).

## Next action

1. Restore the boot selection to slot 1: write p9 `0x10` = 2 (or the live p9
   image) and set eMMC `EXT_CSD` `PARTITION_CONFIG` = `0x50`. The TV needs an
   eMMC programmer or a shop; the board can be mailed. Do not write a boot
   area. See
   [A/B failure](docs/research/48-ab-switch-failure-2026-11-22.md) and
   [recovery gate](docs/guides/recovery-gate.md).
2. Map the `ndp_led` 2D/3D channels and move to the HDMI and Ambilight ioctls.
   See [ndp_led backlight](docs/research/39-ndp-led-pwm-backlight-2026-11-20.md).
3. Keep a second copy of the 2026-11-14 backup off the TV.
4. The A/B switch to slot 0 is TESTED-NEGATIVE; slot 0 is not licensed. The
   old slot 1/boot1 is the only bootable pair. Do not repeat the switch. See
   [A/B failure](docs/research/48-ab-switch-failure-2026-11-22.md).
5. Patch `libfwup` RSA (`nvtfw_sec_verify_whole_img_sign` `0xb889` or
   `nvtfw_enable_secure_boot` `0x6d3d`) and the app-layer version check. Build
   a modified VER40 package, starting with a harmless component, and keep the
   old pair recovery.
6. The classic eburner USB entry remains open. The serial console is the
   diagnostic if that route continues. See
   [NDAL V4L2](docs/research/32-ndal-v4l2-reset-2026-11-14.md).
7. The corrupted-image restore is still the gate for modified boot-area
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
- [Level 3.5 kernel carrier](docs/research/37-kernel-carrier-level-3-5.md)
- [Runtime verifier patch](docs/research/38-runtime-verifier-patch-2026-11-20.md)
- [ndp_led PWM backlight](docs/research/39-ndp-led-pwm-backlight-2026-11-20.md)
- [NFSB mount-path verifier](docs/research/40-nfsb-mount-check-2026-11-20.md)
- [Full NFSB dm mapping](docs/research/43-nfsb-dm-mapping-2026-11-22.md)
- [dm-verity data path](docs/research/44-nfsb-verity-data-path-2026-11-22.md)
- [Custom NFSB mount](docs/research/45-custom-nfsb-mount-2026-11-22.md)
- [Level 4 boot-chain map](docs/research/46-level4-boot-chain-map-2026-11-22.md)
- [A/B switch failure](docs/research/48-ab-switch-failure-2026-11-22.md)
- [43PUS7608/12 field scan](docs/research/34-tpn236e-43pus7608-2026-11-14.md)
- [43PUS7608/12 169.001 static follow-up](docs/research/35-tpn236e-169001-static-2026-11-15.md)
- [43PUS7608/12 169.001 corrections](docs/research/36-tpn236e-169001-corrections-2026-11-16.md)
- [43PUS7608/12 RPC-injection root](docs/research/42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md)
- [55PUS8108/12 field report](docs/research/41-tpn236e-55pus8108-2026-11-21.md)
- [2026-11-14 backup evidence](evidence/deep/2026-11-14-emmc-backup.md)
- [2026-11-14 NDAL evidence](evidence/deep/2026-11-14-ndal-v4l2-reset.md)
