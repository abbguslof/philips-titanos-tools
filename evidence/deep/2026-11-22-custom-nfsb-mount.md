# 2026-11-22 custom NFSB image mount (Level 3.5)

Status: **VERIFIED (hardware)** for a minted SquashFS + NFSB header/tree mounted
read-only on a loop copy. The one-data-block variant is **TESTED-NEGATIVE /
EXPLAINED** (dm-verity zero hash levels).

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [dm-verity data path](2026-11-22-nfsb-verity-data-path.md) and
`tools/nfsb_verity.py`.

## Build

- `custom.sqsh`: `mksquashfs` `-comp lzo`, 4096 bytes, `hello.txt` and
  `etc/custom_marker`.
- Data region 1 MiB (256 x 4096), tree 3 blocks (2 level-0 + 1 top).
- Header: stock `fs1` header with `0x0a=2048`, `0x12=256`; salt/algorithm/block
  sizes unchanged.
- Root digest: `9b253230…`.
- Image `sha256 708f01e5…`, 1,064,960 bytes.

## One-block edge

A 4096-byte data image was rejected: `data block 0 is corrupted`. `veritysetup`
confirmed the rule: one data block has zero hash levels, so the root is
`H(salt || data)` and there is no tree block. The rebuilt single-block image
root is `1a85d2fb…` (matches `veritysetup`); `tools/nfsb_verity.py` now handles
it.

## Live run

| Item | Value |
| :--- | :--- |
| loop | `/dev/loop0`, read-only, 2080 sectors |
| `nvt_dm_setup_linear` | 1; linear `253:10`, size 2072 |
| `nvt_dm_setup_nfsb` | 1; verity `253:11`, size 2048 |
| node | `/dev/mapper/loop0` |
| mount | `mount -t squashfs -o ro` rc 0 |
| `hello.txt` | `custom NFSB mount 2026-11-22` |
| `etc/custom_marker` | `marker` |
| umount | rc 0 |

dmesg:

```text
dm: target linear of size 2072 on 253:10(253:10) is ready
device-mapper: verity: sha256 using implementation "sha256-ce"
dm: target verity of size 2048 on 253:11(253:11) is ready
```

## Rollback

`reboot -f`. After boot: same kernel; `ndp_logo` seloff module; policy export
`b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`; live
`/dev/mapper`; `/dev/linear-*` and `/dev/nfsb-*` back to `2..5`; `fs1` header
`NFSB`; vendor `/swdl/autorun.upg` `74d2790a…`.

## Notes

- Read-only loop copy; the live rootfs and `/dev/nfsb-*` were not used.
- Absolute kernel addresses are not published.
- The minted header keeps the stock RSA signature, which is invalid for the
  changed fields; the direct setup call skips the header check. A real
  `mount -t nfsb` would still reject it unless `nfsb_verify` is patched.
- This is a runtime, read-only path; a bootable modified NFSB remains blocked.
