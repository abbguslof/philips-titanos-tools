# 2026-11-22 NFSB dm-verity data path (Level 3.5)

Status: **VERIFIED (hardware)** for a modified data block passing dm-verity after
a recomputed tree and updated header root digest. **OPEN** for a bootable
modified NFSB and for a custom mountable NFSB rootfs.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [full NFSB dm mapping](2026-11-22-nfsb-dm-mapping.md).

## Format check

The stock `fs1` image (`sha256 2dbca39e…`) was used to verify the tree:

| Item | Value |
| :--- | :--- |
| data offset | `0x1000` |
| data blocks | 4760 x 4096 |
| hash blocks | 38 level-0 + 1 top |
| hash start block | 4760 |
| tree offset | `0x1000 + 4760 * 4096` |
| salt | 32 bytes from header `0x2e` |
| stock root (recomputed) | `6bdf03ba…` = header `0x6f` |
| layout | highest level first, level 0 last |

## Modified image

- Block 100 overwritten with `MODIFIED-DATA-PATH-2026-11-22` then `0x41` fill.
- Rebuilt image: same data with the tree recomputed and the header root at
  `0x6f` replaced. New root `793be4ea…`.
- Control image: same modified data with the stock tree and stock header.

## Results

| Case | Tree / digest | Block 100 | Block 101 |
| :--- | :--- | :--- | :--- |
| Control | stock / stock | EIO; `data block 100 is corrupted` | read OK |
| Rebuilt | recomputed / recomputed | read OK; `MODIFIED-DATA-PATH-2026-11-22AAA` | read OK, identical to control |

Nodes and sizes:

| Mapping | linear | verity | verity node | sizes |
| :--- | ---: | ---: | :--- | :--- |
| Control | `253:10` | `253:11` | `/dev/mapper/loop0` | 61432 / 38080 |
| Rebuilt | `253:12` | `253:13` | `/dev/mapper/loop1` | 61432 / 38080 |

- The rebuilt block matched the local modified block
  (`sha256 27112b64…`).
- Block 101 matched byte-for-byte between both mappings
  (`sha256 15eb6f39…`).
- dmesg for the rebuilt verity target showed only the ready lines, no
  `corrupted` message.

## Rollback

`reboot -f`. After boot: same kernel; `ndp_logo` seloff module; policy export
`b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`; live
`/dev/mapper`; `/dev/linear-*` and `/dev/nfsb-*` back to `2..5`; `fs1` header
`NFSB`; vendor `/swdl/autorun.upg` `74d2790a…`.

## Notes

- Read-only loop copies only; the live rootfs and `/dev/nfsb-*` were not used.
- Absolute kernel addresses are not published.
- The proof is a raw block read through the verity device, not a mounted
  modified SquashFS.
- A bootable modified NFSB is still blocked by the boot-time verifier and
  dm-verity.
