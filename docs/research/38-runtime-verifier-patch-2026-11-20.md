# 2026-11-20 runtime verifier patch (Level 3.5)

Status: **VERIFIED (hardware)** for the direct `nfsb_verify` patch. The runtime
mount-path check is verified in
[40](40-nfsb-mount-check-2026-11-20.md), and the full `linear` + `verity` dm
mapping in [43](43-nfsb-dm-mapping-2026-11-22.md). The dm-verity data path is
verified in [44](44-nfsb-verity-data-path-2026-11-22.md). No boot-chain,
boot-area, or eMMC writes.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method and carrier: [Level 3.5: reusable kernel carrier](37-kernel-carrier-level-3-5.md).

## Why

The carrier gives a runtime kernel call and read/write primitive. The first
Level 3.5 payload uses it to inspect and patch the NFSB header verifier. The
test is direct: no NFSB mount and no live rootfs access.

## Setup

- Load the carrier. Its `scratch` command returns a 512-byte writable buffer
  in module `.bss`.
- Read the first `0x1b0` bytes of the live `fs1` NFSB header.
- Copy the header into the scratch buffer with `poke`.
- Call `nfsb_verify(buffer)` through the carrier's `call` command.

The header is valid: magic `NFSB`, version 3, signature at `0xb0..0x1af`.

## Results

| Step | Result |
| :--- | :--- |
| Pristine `fs1` header, `nfsb_verify` | `0x0000000000000000` |
| Signature byte `0xb0` flipped `0x85 -> 0x84` | `0x00000000ffffbf00` (rejected) |
| `aarch64_insn_patch_text_nosync(nfsb_verify, 0x52800000)` | returned 0 |
| `aarch64_insn_patch_text_nosync(nfsb_verify + 4, 0xd65f03c0)` | returned 0 |
| Patched bytes at `nfsb_verify` | `0xd65f03c052800000` |
| Modified header after the patch | `0x0000000000000000` |

The patched function is `mov w0,#0; ret`. The module stayed live and the
kernel logged no error. The original prologue is `0xd10343fff800865e`.

## Mount integration is verified

`mount -t nfsb` is not available on this boot:

- `/proc/filesystems` lists no `nfsb` type.
- `/sbin` has no `mount.nfsb` helper.
- `dm_mount_nfsb`, `dm_check_nfsb`, and `dm_setup_nfsb` are init text and are
  no longer readable. The mount helper is gone after boot.

`nvt_dm_setup_nfsb` (runtime, exported) creates the `/dev/nfsb-*` block devices.
It calls `dm_create`, `dm_table_create`, `dm_table_add_target` with the
`verity` target, `dm_setup_md_queue`, `dm_swap_table`, and `dm_resume`. A
read-only `dm_table` probe (`tools/probe/dm_table.c`) shows the standard
`DM_LIST_DEVICES` interface returns no devices; the live mappings are internal to
the NFSB setup.

The full `linear` + `verity` mapping is verified with a loop copy in
[43](43-nfsb-dm-mapping-2026-11-22.md).

## Rollback

- Re-insert `/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko`.
- Reboot with `reboot -f`.
- After reboot, `nfsb_verify` returned to `0xd10343fff800865e`.
- Root, the seloff module, and policy
  `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`
  were intact.
- The carrier file was gone from `/tmp`.

The text patch lives in RAM only. Reboot removes it.

## Next

- Build a custom NFSB image that mounts read-only (header, tree, and mapping are
  known). See [44](44-nfsb-verity-data-path-2026-11-22.md).
- Or move to the next Level 3.5 target: hardware control through the carrier's
  `call` primitive.

## Evidence

[2026-11-20 runtime verifier patch](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-20-runtime-verifier-patch.md).
