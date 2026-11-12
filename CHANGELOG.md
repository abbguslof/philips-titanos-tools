# Changelog

## Unreleased

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
  OP-TEE, dm-verity, and the freetitan overlay drift.
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
