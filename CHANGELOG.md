# Changelog

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
