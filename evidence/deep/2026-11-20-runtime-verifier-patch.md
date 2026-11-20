# 2026-11-20 runtime verifier patch

Status: **VERIFIED (hardware)** for the direct `nfsb_verify` patch. **OPEN** for
the NFSB mount integration.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [research/38](../../docs/research/38-runtime-verifier-patch-2026-11-20.md),
[research/37](../../docs/research/37-kernel-carrier-level-3-5.md).

Kernel addresses and the module scratch address are omitted.

## Carrier

| Item | Value |
| :--- | :--- |
| Vendor module | `a4ca05ce8cdb5163c0004a7ce780d8f482c866edba4745b4d5d20eae869c8985` |
| Carrier module | `76f09b62ad4039322ca8eacdb1485c8a634329a94fb38a85929678eb0c6acd31` |
| Scratch buffer | 512 bytes in the carrier `.bss` |
| KCFI | vendor/clang agree on `0xe01408cd` |

## Header test

The first `0x1b0` bytes of the live `fs1` NFSB header were copied into the
carrier scratch buffer. The header had magic `NFSB`, version 3, and the
signature at `0xb0..0x1af`.

| Case | `nfsb_verify` result |
| :--- | :--- |
| Pristine header | `0x0000000000000000` |
| Signature byte `0xb0` flipped `0x85 -> 0x84` | `0x00000000ffffbf00` |

## Patch

`aarch64_insn_patch_text_nosync` was resolved and called twice:

| Call | Result |
| :--- | :--- |
| `nfsb_verify` with `0x52800000` (`mov w0,#0`) | 0 |
| `nfsb_verify + 4` with `0xd65f03c0` (`ret`) | 0 |

`safe-read nfsb_verify` returned `0xd65f03c052800000`. The modified header then
returned `0x0000000000000000`.

The module stayed live. No kernel error appeared in `dmesg`.

## Mount integration

`/proc/filesystems` has no `nfsb` type, `/sbin` has no `mount.nfsb` helper, and
`/dev/nfsb-2` through `/dev/nfsb-5` are existing device-mapper block devices
for the live NFSB partitions. The mount test is open.

## Rollback

The seloff module was re-inserted and the unit rebooted. After reboot:

- Root returned and the seloff module was loaded.
- `nfsb_verify` read back the original `0xd10343fff800865e`.
- The loaded policy hash was
  `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`.
- `/tmp/ndp_logo_carrier.ko` was gone.

## Limits

- The patch is not persistent; reboot removes it.
- The NFSB mount path was not exercised on this boot.
- The live `/dev/nfsb-*` devices and the live rootfs were not touched.
- No boot-chain, boot-area, or eMMC writes.
