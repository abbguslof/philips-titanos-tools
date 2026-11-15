# Changelog

## 0.4.13 - 2026-11-15

### Added

- `43PUS7608/12` (`TPN236E`) field scan and static notes in
  `docs/research/34`: eight open ports, the expired MQTT certificate, no
  network entry vector, the contributor-local `236.006.135.001` static
  findings, and the open package-artifact table.
- The README model-support row and the research index link the new note.

### Changed

- Removed the unrelated custom-userspace project from public docs and raw
  evidence. The private userspace is out of scope; raw captures omit it.
- `docs/research/03` now states that partition targets are firmware-specific:
  `TPN236E` uses `p16`, while `TPN256E` `fs0`/`fs1` use `p19`/`p20`. The
  no-`quick_debug` and OverlayFS findings are marked `TPN236E`-specific.
- `docs/research/33` links the second field report and records the port
  differences (`8883`/`9080` open, `49152`, `:7788` closed).
- Added a derived VER40 offset table to `docs/research/03`. The package size
  `621,094,116` closes at `0x250524e4`. Rows 16-18 correct the earlier
  derivation; SHA-256 and stored-MD5 values remain open.
- Recorded `:7788` as closed on the `43PUS7608/12` field unit and updated the
  issue #3 line references.
- Test coverage is 72 tests.

## 0.4.12 - 2026-11-14

### Added

- Genuine vendor VER40 USB update verified on the 8000: the app-layer accepted
  `PH_2K25_ALL_EU_NT72690_TPN256E_V056.002.236.191_upgrade.pkg` as
  `autorun.upg`, loaded it, validated it, and programmed active slot 0
  (`p15`/`p17`/`p19`). AC-on activated it; firmware `002.236.191`.
- The eMMC boot area changed: boot0 `1c74949e…` new; boot1 `eee415…` recovery.
  The old main slot 1 (`p16`/`p18`/`p20`) is the recovery pair.
- Root and persistence survived the update: `uid=0`, dropbear `:2222`,
  telnetd `:2323`, `customer_env.sh`, and the persistent root.
- `p9` post-update `7e8fca3d…`; `p1`/`p2`, `p13`/`p14`, `p21` unchanged.

### Changed

- The app-layer RSA verifier is the barrier for a modified package. The next
  route is the patched `libfwup` and a modified VER40 component.
- Test coverage is 72 tests.

## 0.4.11 - 2026-11-14

### Added

- Classic eburner initramfs map: the `eburner` uImage carries a gzip cpio at
  component offset `0xfd8948` with `/etc/init.d/S21eburner.sh`,
  `nvt_extract_sys_run`, and `nvt_eburner`. The script reads a USB image at
  `/media/sda1/nvt_tv_firmware.img` (or `nvt_eburner_img=`), extracts
  `sys_run`, and runs `/tmp/sys_run/run.sh`; it does not read
  `/swdl/autorun.upg`.
- p9 metadata layout: `PPCH` pptbl0/1 at `0x400`/`0xa00`, `FWVR` vinfo at
  `0x1000`, `UPST` at `0x3600`, `BTFG` bflag (inferred) at `0x3800`, and
  `PKG_ready` at `0x3e00`; mapped the `libfwup` bflag/pptbl functions.
- Confirmed `DEV_UART_Set_SWEburnerOnOff` (`/dev/ntkstbc`, ioctl
  `0xc0105310`, 16-byte struct) and the app reset wrappers.
- Tested the full classic package on the USB plus the p9 metadata; the eburner
  produced no `update-proof.txt`, `PKG_SUCCESS`, or p9 markers.

### Changed

- The app-layer `/swdl` path and the classic USB eburner path are separate.
- The eburner entry trigger/boot flag remains open.
- Test coverage is 72 tests.

## 0.4.10 - 2026-11-14

### Added

- `70PUS8108/60` (`TPN236E`) correction: the `POST` `503` was a
  `curl --digest` bodyless-probe artifact, not a TV-side refusal. A body-bearing
  `POST /6/input/key` returned `200` and changed the volume. The same unit
  accepted `1926` control requests without enforcing pairing. This correction
  withdraws the first pairing claim.
- Independent external confirmation of the `TPN236E_236.006.135.001` VER40
  package: `parse_timg.py --verify` reported 19/19 component MD5s OK on a fresh
  public download. Added the reference component list to `docs/research/03`.
- GitHub issue forms for field reports and for tooling, docs, or accessibility
  problems.
- `ACCESSIBILITY.md` with the docs and Ambilight studio scope, known gaps, and
  reporting path.

### Changed

- `tools/jointspace_client.py` accepts a non-JSON 2xx body instead of raising
  on the HTML `Ok` response. Added a regression test.
- `SECURITY.md`, `docs/research/08`, `12`, `33`, `evidence/README.md`, and the
  indexes record the unauthenticated `1926` control surface and the corrected
  `POST` result.
- Test coverage is 72 tests.

## 0.4.9 - 2026-11-14

### Added

- External `70PUS8108/60` (`TPN236E`) field report: read-only network surface,
  JointSpace 6.1 behavior, the POST `503` anomaly, and no network entry vector.
  Status: REPORTED. No raw capture was supplied.
- `docs/research/33-tpn236e-70pus8108-network-surface-2026-11-14.md` and the
  index rows.

### Changed

- Test coverage is 71 tests.

## 0.4.8 - 2026-11-14

### Added

- NDAL V4L2 reset helper test: `NDAL_VideoExt_OpenDevice(0, 0xA)` selects
  `/dev/video24`, then `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` resets the TV.
  One full-wrapper run left `/swdl/autorun.upg` removed; p9 stayed
  `PKG_ready`, `misc + 0x4000` was zero, `/swdl/eburner-proof.txt` was absent,
  and the boot areas were unchanged.
- The raw V4L2 `G_EXT_CTRLS` reset the TV and left the package. The 0.4.11
  entry records the USB/eburner correction.

### Changed

- Corrected the NDAL V4L2 control: id `0x0f170f1f` (AC-on) and `0x0f170f29`
  (plain), class `0x0f170000`, ioctl `0xc0185647`, 20-byte controls with value
  pointers, target `/dev/video24`, provider `libv4l2.so.0`, and the ioctl fd at
  `0x50d90`.
- The eburner entry is open; the 0.4.11 entry maps the classic USB initramfs.
- Test coverage is 71 tests.

## 0.4.7 - 2026-11-14

### Added

- `docs/research/32-ndal-v4l2-reset-2026-11-14.md` and
  `evidence/deep/2026-11-14-ndal-v4l2-reset.md`: the NDAL V4L2 STBC reset
  functions, the initial control reading (`0xf17f1f`, class `0x0f170000`,
  ioctl `0xc0185647`; corrected in 0.4.8), and the next helper.
- Paused-`appmgr` retry: the p9 package stayed staged across the AC cycle, but
  the eburner did not enter (`PKG_ready`, `0x4000` zero, no proof). The STBC/AC
  entry was not repeatable.
- Cleanup: vendor `/swdl/autorun.upg` `74d2790a…`, p9 `c32f354f…`, STBC off,
  boot areas `eee415…`.

### Changed

- Test coverage is 71 tests.

## 0.4.6 - 2026-11-14

### Added

- `ntkctl --data HEX` for an exact hex ioctl buffer.
- Direct `/swdl` staging test results: the eburner was entered via the STBC
  eburner mode and AC-on, consumed the classic package, but the `run.sh` proof
  and `PKG_SUCCESS` did not appear. The app layer restored the vendor package.
- The vendor AC-on reset (`PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` /
  `NDAL`) path and the `gdbserver`/`idtv` failure.

### Changed

- Test coverage is 71 tests.

## 0.4.5 - 2026-11-14

### Added

- Eburner flag mapping: `PKG_ready<path>` at `misc + 0x3e00`, STBC ioctl
  `0xc0105310`, and a no-op eburner status function.
- Direct `/swdl` staging plan in the app-layer update gate note and evidence.

### Changed

- Test coverage is 71 tests.

## 0.4.4 - 2026-11-14

### Added

- App-layer update gate analysis: USB trigger, `/swdl/autorun.upg` is
  `TIMGPKGVER40`, RSA public-key verifier, no private key, and the direct
  `/swdl` staging bypass plan.
- `docs/research/31-app-update-gate-2026-11-14.md` and
  `evidence/deep/2026-11-14-app-update-gate.md`.
- Correction in `docs/research/30`: the app-layer USB update expects
  `TIMGPKGVER40`; the local classic package is not valid for that path.

### Changed

- Test coverage is 71 tests.

## 0.4.3 - 2026-11-14

### Added

- Same-byte restore test on `mmcblk0boot0` and `mmcblk0boot1`: the stock bytes
  were written back, read-back hashes verified, `force_ro` restored, and both
  cold boots returned root. No modified image was written.
- Evidence and recovery docs now record the restore result.

### Changed

- The recovery gate now separates the verified same-byte restore from the still
  open corrupted-image recovery path.
- Test coverage is 71 tests.

## 0.4.2 - 2026-11-14

### Added

- `STATE.md`: current verified state, live drift, and the next gate.
- `docs/guides/recovery-gate.md`: backup and restore runbook for boot-chain
  work.
- `evidence/deep/2026-11-14-emmc-backup.md`: sizes and hashes for the
  recovery-gate backup. Raw images stay off the repo.
- `docs/research/30-update-path-2026-11-14.md` and
  `evidence/deep/2026-11-14-update-path.md`: component map, MD5-only burner
  checks, live slot matches, and the prepared dump-only test package.

## 0.4.1 - 2026-11-14

### Added

- `TIMGPKGVER40` container support (newer 2023+ Titan OS packages) in
  `tools/firmware/parse_timg.py`, including a walk-validated component scan and
  per-component MD5 verification. The format reference and extraction guide
  document both revisions.
- External `77OLED760/12` (TPN258E) report: USB autoroot, `/swdl` persistence,
  and SSH after USB-less cold boots (`evidence/tpn258e-77oled760/`).

### Fixed

- `parse_timg.py --verify --extract` on a VER40 package now extracts after a
  successful per-component check instead of returning early.

### Changed

- Test coverage is 71 tests.

## 0.4.0 - 2026-11-12

### Added

- Redacted external autoroot evidence for the `55PUS8450/12` variant
  (`evidence/tpn256e-variant/`). The logs confirm the USB root path and the
  `mmcblk0p19` root partition; the `/swdl` persistence result remains REPORTED
  until a USB-less `root_boot.log` is available.
- `tools/deep_probe.py`: redacted read-only live inventory for the 8000 lab and
  field units.
- `tools/bootchain_dump.py`: read-only local pull of the 8000 boot areas and
  metadata partitions.
- `tools/bootchain_inspect.py`: local uImage header/data CRC, entropy, embedded
  image, and marker inspection.
- `tools/boot_metadata.py`: local `PPCH`/`STBC`/`VTBL` parsing and `p9` boot
  metadata scanning.
- `payloads/emmc_backup.sh`: read-only full eMMC user-area and boot-area
  backup to a mounted USB filesystem.
- Deep-jailbreak roadmap, recovery-engineering plan, 8450 portability plan,
  boot-image map, and update-package map (`docs/research/25`-`29`).
- Deep boot-chain evidence summary (`evidence/deep/`).

### Changed

- Front-facing docs now present the toolkit for Philips TVs running Titan OS on
  the Novatek NT72690 platform. The `55PUS8000/12` is named as the maintainer's
  tested model, other models are marked untested, and reports or PRs for other
  models are invited.
- Test coverage is 67 tests.

## 0.3.0 - 2026-11-11

### Added

- Repo banner at `assets/banner.svg` for the front README.
- Firmware-variant persistence via the vendor `/swdl/telnet/telnetd` seam
  (`docs/research/24`), reported and hardware-tested by **Pedram** on
  `55PUS8450/12`, firmware `TPN256E_V056.010.032.001`. The report is labelled
  `REPORTED`; it is not independently reproduced by this repo.
- Research note 24 records the negative result (`customer_env.sh` absent from
  `run.sh`), the working `/swdl` wrapper, the USB-less cold-boot check, and the
  other `/swdl` service seams as open follow-ups.
- `payloads/persist_root.sh` now detects whether `run.sh` sources
  `customer_env.sh` or whether `run_custom_impl.sh` has the
  `/swdl/telnet/telnetd` check, and installs the matching hook. It aborts
  without writing if neither is present.
- `REPORTED` status label for external hardware reports.

### Changed

- Rebuilt the front README around a quick-start path, firmware-hook diagram,
  verification tables, tool index, and proof section.
- Persistent-root and restore-to-stock guides now diagnose the live hook before
  installing and cover both variants.
- Glossary, payload, partition, research cross-reference, and index docs cover
  `/swdl` and both hooks.
- Test coverage is 43 tests.
- Version 0.3.0.

## 0.2.0 - 2026-11-10

### Added

- Live inventory (`docs/research/18`): boot, SELinux, mounts, device nodes,
  OP-TEE, dm-verity, and the live overlay drift.
- Control-surface map (`docs/research/19`): the measured `ntkmem` ABI
  (`0x35`, `0x4d01`, `0x4d02`), V4L2 HDMI, and a GPIO line census, plus the
  static harnesses in `tools/probe/`.
- Non-resetting USB stateproof autoscript
  (`payloads/autoscript.stateproof.txt`) and the v8 evidence set.
- Install prefix on `/mtd_rwarea/apdat/opt` with a static `lsblk`
  (`docs/research/21`, `tools/install/`).
- USB-less persistence for the prefix (`docs/research/22`).
- Static key-only Dropbear SSH on `:2222` (`docs/research/23`,
  `payloads/root_boot.opt-block.sh`) with build, live, and cold-boot evidence.
- Publication audit (`PUBLICATION_AUDIT.md`).

### Changed

- `root_boot.sh` appends `/mtd_rwarea/apdat/opt/bin` to `PATH` and runs the
  opt/SSH block after the boot firewall.
- Documented the vendor `chmod 777 -R /mtd_apdat` at `run.sh:587`; the SSH hook
  uses a tmpfs `/root` to survive it.
- Third-party notices cover Dropbear and Zig.
- Version 0.2.0.

### Fixed

- Normalized the placeholder production code in the NVM format document to
  `TW000000000000`.

## 0.1.1 - 2026-11-05

### Added

- Runtime NFSB research: the inner SquashFS at offset `0x1000` mounts directly
  with the stock `squashfs` driver, without the `nfsb` verifier or dm-verity.
- `payloads/nfsb_raw_mount.sh` for a read-only mount of an NFSB partition.
- Runtime NFSB evidence for the pristine mount, the modified-block verity
  failure, and the direct SquashFS mount.
- Partition and NVM clarification: `misc` is p9, `nvm_dat` is p11, and the
  SAM wrapper uses partition ID 9.

### Changed

- Clarified that the runtime raw mount does not defeat the boot-time NFSB
  verifier. A modified NFSB image still cannot boot or flash.
- Test count is 40.

## 0.1.0 - 2026-10-30

First public, sanitized release.

### Added

- Verified USB autorun root path (`tools/autoroot_usb.py`,
  `payloads/autoroot.sh`, `payloads/autoroot.txt`).
- Persistent root hook (`payloads/persist_root.sh`) using
  `/mtd_rwarea/apdat/customer_env.sh`.
- Public research documents for the XBoot/ATF boot chain, flash layout,
  `TIMG`/`PIMG`/`NFSB` firmware container, NVM format, USB autorun, hardware
  `SERV.U`, JointSpace, SAM, channel maps, and network telemetry.
- Guides for firmware acquisition/extraction, USB autoroot, persistent root,
  restore, SAM export/import, and testing.
- Curated, redacted evidence for v1-v8 (including the persistent boot) and the UMFG partition slices.
- Glossary and ADRs for the two USB workflows, the persistence hook, evidence
  redaction, and public-release structure.

### Changed

- Removed the hardcoded JointSpace application secret; pairing now reads
  `PHILIPS_APP_SECRET` or `PHILIPS_APP_SECRET_FILE`.
- Replaced real device identifiers and private addresses with documentation
  ranges.
- Corrected stale claims: rootfs p20, pstore p36, `apdat` p31, 40 partitions,
  XBoot (not an interactive U-Boot), `tvtype: consumer` userspace lock, and the
  distinction between container MD5 and inner `NFSB` RSA/SHA-256.
- Renamed `payload/` to `payloads/` and split `usbdump/` into `samples/` and
  `evidence/`.

### Removed

- Raw firmware packages, extracted vendor filesystems, raw packet captures,
  multi-megabyte logs with device identifiers, duplicate vendor dumps, private
  keys, and live pairing credentials.
