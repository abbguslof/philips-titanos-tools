# 2026-11-22 full NFSB dm mapping (Level 3.5)

Status: **VERIFIED (hardware)** for `nvt_dm_setup_linear` + `nvt_dm_setup_nfsb`
with a loop copy; the verity device mounts the stock SquashFS read-only.
**OPEN** for the dm-verity data path.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [carrier](../../docs/research/37-kernel-carrier-level-3-5.md) and the
[mount-path check](2026-11-20-nfsb-mount-check.md).

## Setup

- Read-only loop copy of `fs1`, 31,457,280 bytes (61440 sectors), attached at
  `/dev/loop0`.
- The `fs1` NFSB header was placed in the carrier scratch buffer. The input
  `dev_t` was loop `7:0`.
- `nvt_dm_setup_linear(header, &dev_t)` then
  `nvt_dm_setup_nfsb(header, &dev_t, "/dev/loop0", out)`.

## Header values (big-endian)

| Offset | Value |
| :--- | ---: |
| version (`0x04`) | 3 |
| verity version (`0x05`) | 1 |
| start sector (`0x06`) | 8 |
| data length sectors (`0x0a`) | 38080 |
| data block count (`0x12`) | 4760 |
| data block size (`0x16`) | 4096 |
| hash block size (`0x2a`) | 4096 |
| algorithm (`0x1a`) | `sha256` |
| salt (`0x2e`) | 64 hex chars |
| root digest (`0x6f`) | 64 hex chars |
| signature (`0xb0`) | 256 bytes |

Computed `hash_start_block = 38080 * 512 / 4096 = 4760`.

## Results

| Step | Result |
| :--- | :--- |
| `nvt_dm_setup_linear` | `1`; linear `dev_t` `253:10` |
| `nvt_dm_setup_nfsb` | `1`; verity `dev_t` `253:11`; out `/dev/mapper/loop0` |
| `/dev/linear-6` | `7:0` (loop input) |
| `/dev/nfsb-6` | `253:10` (linear dm) |
| `/dev/mapper/loop0` | `253:11` (verity dm) |
| linear target size | `61432` (`61440 - 8` sectors) |
| verity target size | `38080` sectors |
| `mount -t squashfs -o ro /dev/mapper/loop0` | rc 0 |
| rootfs read | `bin`, `etc/init.d/S21idtv.sh`, `apexe_ext`, ... |
| `umount` | rc 0 |

dmesg:

```text
dm: target linear of size 61432 on 253:10(253:10) is ready
device-mapper: verity: sha256 using implementation "sha256-ce"
dm: target verity of size 38080 on 253:11(253:11) is ready
```

These are the same lines the boot-time NFSB mount prints.

## Rollback

`reboot -f`. After boot: same kernel; `ndp_logo` seloff module loaded; policy
export `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`;
`/dev/mapper` back to `apexe_ext`, `control`, `mtd_apexe`; `/dev/linear-6` and
`/dev/mapper/loop0` gone; `fs1` header `NFSB`; vendor `/swdl/autorun.upg`
`74d2790a…`.

## Notes

- The live rootfs and `/dev/nfsb-*` were not used; only a loop copy.
- Absolute kernel addresses were resolved from `/proc/kallsyms` at run time and
  are not published.
- A modified data block still fails dm-verity; the rebuilt-tree test is the next
  gate.
