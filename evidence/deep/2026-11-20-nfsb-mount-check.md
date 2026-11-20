# 2026-11-20 NFSB mount-path verifier

Status: **VERIFIED (hardware)** for the runtime `nvt_dm_check_nfsb` check with a
modified loop copy and the patched `nfsb_verify`. **OPEN** for the full
`nvt_dm_setup_nfsb` dm mapping.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [research/40](../../docs/research/40-nfsb-mount-check-2026-11-20.md),
[research/38](../../docs/research/38-runtime-verifier-patch-2026-11-20.md),
[research/37](../../docs/research/37-kernel-carrier-level-3-5.md).

Kernel addresses are omitted.

## Setup

| Item | Value |
| :--- | :--- |
| Carrier | `76f09b62ad4039322ca8eacdb1485c8a634329a94fb38a85929678eb0c6acd31` |
| Source image | live `fs1`, 31,457,280 bytes |
| Change | NFSB signature byte `0xb0`, `0x85 -> 0x84` |
| Loop | `/dev/loop0` |
| Check | `nvt_dm_check_nfsb(header, "/dev/loop0")` |

`nvt_dm_check_nfsb` returns 1 on success and 0 on failure.

## Results

| Case | Return | dmesg |
| :--- | ---: | :--- |
| Unpatched, modified signature | `0` | `nfsb: header verification failed` |
| Patch `nfsb_verify` with `0x52800000` | `0` | |
| Patch `nfsb_verify + 4` with `0xd65f03c0` | `0` | |
| Patched bytes | | `safe-read` returned `0xd65f03c052800000` |
| Patched, modified signature | `1` | `NFSB header found and verified` |

The patched verifier accepts the modified header through the runtime mount-path
check.

## Rollback and reboot

- `losetup -d /dev/loop0`; remove `/tmp/nfsb-loop.bin`.
- Unload the carrier and restore `/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko`.
- Reboot with `reboot -f`.
- After reboot, `nfsb_verify` returned to `0xd10343fff800865e`.
- Root, the seloff module, and policy
  `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`
  were intact.

## Full mapping is open

`nvt_dm_setup_nfsb` creates the `/dev/nfsb-*` block devices with the internal
dm API:

- `dm_create`
- `dm_table_create`
- `dm_table_add_target` with the `verity` target
- `dm_setup_md_queue`
- `dm_swap_table`
- `dm_resume`

The `dm_mount_nfsb`, `dm_check_nfsb`, and `dm_setup_nfsb` helpers are init-only
and are gone after boot. A read-only `dm_table` probe
(`tools/probe/dm_table.c`) shows the standard `DM_LIST_DEVICES` interface
returns no devices, and `DM_TABLE_STATUS` with the visible names returns ENXIO.

A full mount test needs a direct `nvt_dm_setup_nfsb` call with a loop block
device and the right arguments. That call also creates a verity target, so a
modified data block still needs the verity path.

## Limits

- The live rootfs and the live `/dev/nfsb-*` devices were not touched.
- No boot-chain, boot-area, or eMMC writes.
- The full dm mapping is not tested.
