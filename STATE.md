# Current state

Updated: 2026-11-14.

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
| Boot areas | `mmcblk0boot0`/`boot1` 4 MiB, identical, `force_ro=1`, `ro=1`, sha256 `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd` | [2026-11-14 backup](evidence/deep/2026-11-14-emmc-backup.md) |
| Boot map | `p1`/`p2` UMFG slots; `p9` slot map; `p13`/`p14` ATF; `p15`/`p16` FDT; `p17`/`p18` kernel; `p19`/`p20` rootfs; `p21` plain `kerupm` | [Boot image map](docs/research/28-boot-image-map.md) |
| Recovery backup | Full `mmcblk0` image and boot areas; `sha256sum -c` passes | [2026-11-14 backup](evidence/deep/2026-11-14-emmc-backup.md) |
| Restore | Same-byte write to both boot areas, read-back hashes, and cold boots verified | [2026-11-14 backup](evidence/deep/2026-11-14-emmc-backup.md) |
| Update package | `sys_run`/`kerupm`/`eburner` map; `kerupm` matches `p21`; burner checks are MD5-only | [Update path](docs/research/30-update-path-2026-11-14.md) |
| App-layer update gate | USB package stages to `/swdl/autorun.upg`; the live file is `TIMGPKGVER40`; the verifier is RSA; no private key. The eburner entered twice via STBC + AC; the script did not leave a proof. A paused-appmgr retry kept the package but did not enter | [App-layer gate](docs/research/31-app-update-gate-2026-11-14.md) |
| NDAL V4L2 reset | `NDAL_VideoExt_STBC_ResetByHWWDT_*` builds control `0xf17f1f` (class `0x0f170000`) and ioctl `0xc0185647`; the helper is open | [NDAL V4L2](docs/research/32-ndal-v4l2-reset-2026-11-14.md) |
| `/swdl` and p9 | Vendor `74d2790a…`, p9 `c32f354f…`, STBC off, boot areas `eee415…` | [NDAL evidence](evidence/deep/2026-11-14-ndal-v4l2-reset.md) |
| Runtime NFSB | Inner SquashFS mounts read-only at offset `0x1000` | [Runtime NFSB](docs/research/17-runtime-nfsb-squashfs.md) |

## Live drift

The public repo documents research and root. The live unit is further along:

- `/tmp/freetitan-root` is mounted (SquashFS root, ext4 data binds).
- `/root` is a 700 tmpfs; `/etc/profile.d` is bind-mounted from `apdat`.
- `/mtd_rwarea/apdat` holds `customer_env.sh` (3513 B), `root_boot.sh`,
  `busybox`, `policy.33.perm.bin`, `ndp_logo_boot.ko`,
  `ndp_logo_seloff_boot.ko`, `opt/`, and the freetitan scripts and logs.
- `/swdl` holds `autorun.upg` (917,372,175 B), `boot0.bin`, `policy33.bin`, and
  the freetitan directory.
- The 2026-11-14 eburner retries restored the vendor `/swdl/autorun.upg`, the
  p9 `misc`, and the STBC mode; the boot areas are unchanged.
- The freetitan custom rootfs is outside this repository's public scope. This
  page records its presence, not its internals.

## Open gates

- [x] Full eMMC and boot-area backup (2026-11-14).
- [x] Same-byte restore test: wrote the stock bytes back to `mmcblk0boot0` and
  `mmcblk0boot1`, read back the hashes, restored `force_ro`, and cold-booted
  both times. See [backup evidence](evidence/deep/2026-11-14-emmc-backup.md).
- [ ] Corrupted-image restore: prove recovery from a deliberately corrupted
  boot area. This needs the eMMC boot-area selection or ISP/JTAG path.
- [x] App-layer USB update trigger: USB package -> `/swdl/autorun.upg` ->
  verify -> eburner flag -> reset. See
  [app-layer gate](docs/research/31-app-update-gate-2026-11-14.md).
- [x] Eburner flag path: `PKG_ready<path>` at `misc + 0x3e00`, STBC ioctl
  `0xc0105310`, and a no-op status function. See
  [app-layer gate](docs/research/31-app-update-gate-2026-11-14.md).
- [x] Eburner trigger: the STBC eburner mode + `PKG_ready` + AC-on entered the
  eburner twice and consumed the classic package. The script did not leave
  `PKG_SUCCESS` or the proof. A paused-appmgr retry kept the package but did
  not enter.
- [ ] Update environment script/loader: the p9 metadata package did not enter;
  the `insmod`/`/swdl`/`$BB` and the loader checks remain candidates. The app
  layer removes or restores the package.
- [ ] Direct `/swdl` staging test: partial. The p9 metadata package and a
  pre-`insmod` proof did not fix the STBC/AC entry.
- [ ] NDAL V4L2 reset helper: decompile `NDAL_VideoExt_STBC_ResetByHWWDT`
  (`0x137f0`) and `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` (`0xb6ad1`), resolve
  the `v4l2_open` provider and the `/dev/video%i` index, and build the helper.
- [x] `kerupm` package/live match: plain uImage, valid data CRC, exact bytes at
  `p21`. Update-mode selection is still open.
- [ ] `p1`/`p2` FIT and `VTBL`/`NVHC` verifier map. The `p9` `PPCH` slot map is
  decoded; the live `VTBL`/`STBC` differ from the package.
- [ ] Generalize the kernel carrier.
- [ ] Dual-boot or external recovery slot.

## Next action

1. Keep a second copy of the 2026-11-14 backup off the TV.
2. The same-byte restore passed. Before a modified boot image, prove the
   corrupted-image recovery path.
3. Read-only: decompile `NDAL_VideoExt_STBC_ResetByHWWDT` (`0x137f0`) and
   `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` (`0xb6ad1`), the four defined
   `ndcommon_v4l2_*` bodies (`0x27534`/`0x27554`/`0x27574`), and dump
   `.rodata` `0x2ca54` (`/dev/video%i`) and `0x2cbd0` (`gv4l2_dev_name`). Still
   resolve the `v4l2_open`/`v4l2_ioctl` provider and the `/dev/video%i` index.
   See [NDAL V4L2](docs/research/32-ndal-v4l2-reset-2026-11-14.md).
4. Build the V4L2 reset helper (dynamic `libNDAL_EX.so` or direct
   `VIDIOC_S_EXT_CTRLS` with id `0xf17f1f`, class `0x0f170000`, value 1).
5. Test with the p9 package; read p9 `0x3e00`/`0x4000` and
   `/swdl/eburner-proof.txt`; restore the vendor `/swdl`, the p9 `misc`, and
   the STBC mode.

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
- [2026-11-14 backup evidence](evidence/deep/2026-11-14-emmc-backup.md)
- [2026-11-14 NDAL evidence](evidence/deep/2026-11-14-ndal-v4l2-reset.md)
