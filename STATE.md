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
| Update package | `sys_run`/`kerupm`/`eburner` map; `kerupm` matches `p21`; burner checks are MD5-only | [Update path](docs/research/30-update-path-2026-11-14.md) |
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
- The freetitan custom rootfs is outside this repository's public scope. This
  page records its presence, not its internals.

## Open gates

- [x] Full eMMC and boot-area backup (2026-11-14). Restore not tested.
- [ ] Restore test: write the same bytes back, cold boot, verify. The boot
  areas are `force_ro=1`; the write procedure is unproven.
- [ ] Update trigger and loader map. Component map and burner checks are done;
  the trigger and the app-layer RSA gate are open. See
  [update path](docs/research/30-update-path-2026-11-14.md).
- [ ] Dump-only `sys_run` package test. The package is prepared; it is blocked
  on the restore test.
- [x] `kerupm` package/live match: plain uImage, valid data CRC, exact bytes at
  `p21`. Update-mode selection is still open.
- [ ] `p1`/`p2` FIT and `VTBL`/`NVHC` verifier map. The `p9` `PPCH` slot map is
  decoded; the live `VTBL`/`STBC` differ from the package.
- [ ] Generalize the kernel carrier.
- [ ] Dual-boot or external recovery slot.

## Next action

1. Keep a second copy of the 2026-11-14 backup off the TV.
2. Decide on the restore test. Use the stock bytes first; do not write a
   modified image.
3. Read-only work that can proceed now: review the
   [update path](docs/research/30-update-path-2026-11-14.md), map the update
   trigger and the `libfwup.so` gate, and inspect the `sub_123ac` partition
   write order. The dump-only `sys_run` package is prepared in `dist/` and is
   blocked on the restore test.

## Stop conditions

- No full backup.
- No verified restore.
- No way to select or recover the boot area.
- Field units (`TPN236E`, `TPN258E`, `TPN256E` variants): read-only only.

## Links

- [Recovery gate](docs/guides/recovery-gate.md)
- [Deep jailbreak roadmap](docs/research/25-deep-jailbreak-roadmap.md)
- [Recovery engineering](docs/research/26-recovery-engineering.md)
- [Boot image map](docs/research/28-boot-image-map.md)
- [Update package map](docs/research/29-update-package-map.md)
- [Update path](docs/research/30-update-path-2026-11-14.md)
- [2026-11-14 backup evidence](evidence/deep/2026-11-14-emmc-backup.md)
