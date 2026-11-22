# Custom NFSB image: mint and mount

Status: **VERIFIED (hardware) 2026-11-22** for a minted SquashFS + NFSB
header/tree mounted read-only through `nvt_dm_setup_linear` +
`nvt_dm_setup_nfsb` on a loop copy. The one-data-block variant is
**TESTED-NEGATIVE / EXPLAINED**: dm-verity has zero hash levels for a single
data block, so the root is `H(salt || data)` and there is no tree block.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [full NFSB dm mapping](43-nfsb-dm-mapping-2026-11-22.md),
[dm-verity data path](44-nfsb-verity-data-path-2026-11-22.md), and
`tools/nfsb_verity.py`.

## Why

Doc 44 proved that a modified data block verifies after a rebuilt tree. This
mints a whole new image from a host-built SquashFS and mounts it, which proves
the header/tree builder end to end.

## Build

```sh
mksquashfs custom-root custom.sqsh -comp lzo -noappend -all-root -no-xattrs
```

The NFSB header is the stock `fs1` header with only the data geometry changed:

- `0x0a` data length in 512-byte sectors,
- `0x12` data block count,
- salt, algorithm, block sizes, version, and the rest are kept;
- `tools/nfsb_verity.py rebuild` writes the tree and the ASCII root digest at
  `0x6f`.

The verified image pads the SquashFS to a 1 MiB data region (256 blocks) so the
SquashFS driver's 128 KiB reads stay inside the verity device. That gives a
two-level tree (2 level-0 blocks + 1 top block).

### The one-block edge

A first attempt with a 4096-byte data region (one data block) was rejected with
`data block 0 is corrupted`. The cause is dm-verity's level rule, confirmed
offline with `veritysetup`:

| Data blocks | Hash levels | Root |
| ---: | ---: | :--- |
| 1 | 0 | `H(salt \|\| data)`; no tree block |
| 2-128 | 1 | `H(salt \|\| level-0 block)` |
| 129-16384 | 2 | `H(salt \|\| top block)` |

`tools/nfsb_verity.py` now returns the data hash and an empty tree for a single
data block; a rebuilt single-block image verifies
(`1a85d2fb…`, matching `veritysetup`).

## Live run

| Step | Result |
| :--- | :--- |
| Image | 1,064,960 bytes (2080 sectors), data 256 x 4096, tree 3 x 4096 |
| `nvt_dm_setup_linear` | 1; linear `253:10`, size 2072 |
| `nvt_dm_setup_nfsb` | 1; verity `253:11`, size 2048; node `/dev/mapper/loop0` |
| `mount -t squashfs -o ro /dev/mapper/loop0` | rc 0 |
| `hello.txt` | `custom NFSB mount 2026-11-22` |
| `etc/custom_marker` | `marker` |
| `umount` | rc 0 |

dmesg:

```text
dm: target linear of size 2072 on 253:10(253:10) is ready
device-mapper: verity: sha256 using implementation "sha256-ce"
dm: target verity of size 2048 on 253:11(253:11) is ready
```

## Rollback

`reboot -f`. After boot: same kernel, `ndp_logo` seloff module, policy export
`b43297b1…`, live `/dev/mapper`, `/dev/linear-6` and `/dev/mapper/loop0` gone,
`fs1` header `NFSB`, vendor `/swdl/autorun.upg` `74d2790a…`.

## What this means

- The NFSB header and hash tree can be minted from a host-built SquashFS, and
  the kernel's dm-verity accepts the result.
- The minted header carries the stock RSA signature, which is not valid for the
  changed fields. The setup is called directly, so the header check is
  bypassed; a real `mount -t nfsb` still needs the `nfsb_verify` patch
  ([38](38-runtime-verifier-patch-2026-11-20.md),
  [40](40-nfsb-mount-check-2026-11-20.md)).
- This is a runtime, read-only path. It does not make a bootable modified NFSB.

## Limits and safety

- Lab-only, hardware-only. Use a loop copy; do not touch the live rootfs or
  `/dev/nfsb-*`.
- The image is unsigned in the NFSB header sense; the direct setup call skips
  the header check.
- A bootable modified NFSB still needs the Phase R recovery path or a
  boot-chain verifier bypass.

## Evidence

[2026-11-22 custom NFSB mount](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-22-custom-nfsb-mount.md).

## Related

- [dm-verity data path](44-nfsb-verity-data-path-2026-11-22.md)
- [Full NFSB dm mapping](43-nfsb-dm-mapping-2026-11-22.md)
- [Runtime NFSB raw SquashFS mount](17-runtime-nfsb-squashfs.md)
- [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md)
