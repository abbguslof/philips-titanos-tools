# Full NFSB dm mapping: `linear` + `verity` (Level 3.5)

Status: **VERIFIED (hardware) 2026-11-22** for the full runtime dm mapping with a
loop copy: `nvt_dm_setup_linear` and `nvt_dm_setup_nfsb` build the `linear` and
`verity` targets, and the verity device mounts the stock SquashFS read-only. The
dm-verity data path is verified in
[44](44-nfsb-verity-data-path-2026-11-22.md). No boot-chain, boot-area, or eMMC
writes.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [Level 3.5 carrier](37-kernel-carrier-level-3-5.md), the
[verifier patch](38-runtime-verifier-patch-2026-11-20.md), and the
[mount-path check](40-nfsb-mount-check-2026-11-20.md).

## Why

Doc 40 verified `nvt_dm_check_nfsb` against a modified loop header. The full
`nvt_dm_setup_nfsb` dm mapping was the next gate. This test reverses both setup
functions, calls them with a loop block device, and mounts the result.

## The two functions

Both are exported kernel symbols. Their bodies are reachable through the carrier
and were resolved from `/proc/kallsyms`; absolute addresses are not published.

### `nvt_dm_setup_linear(header, &dev_t)`

- builds `/dev/linear-N` (`N = nfsb_dev_id + 2`) as a node for the **input**
  `dev_t` (the raw partition or loop device);
- creates a dm device with one target of type `linear`, length
  `device_sectors - start`, params `"<node> <start>"`, where
  `start = header[0x06]` in 512-byte sectors;
- writes the new **linear** dm `dev_t` back to `&dev_t` and returns 1.

### `nvt_dm_setup_nfsb(header, &dev_t, path, out)`

- builds `/dev/nfsb-N` (`N` as above) as a node for the **input** `dev_t` (the
  linear dm device);
- creates a dm device with one target of type `verity`, length
  `header[0x0a]` sectors, params
  `"<ver> <data> <hash> <data_bs> <hash_bs> <nblocks> <hash_start> <algo> <digest> <salt>"`,
  with `data = hash = /dev/nfsb-N`;
- builds `/dev/mapper/<basename(path)>` as a node for the **verity** dm device,
  writes that name to `out`, updates `&dev_t`, returns 1;
- increments `nfsb_dev_id`.

The two calls chain: `setup_linear` turns the raw device into a data-area
mapping, and `setup_nfsb` puts verity on top of it. The live boot aliases show
the same chain: `/dev/linear-*` (raw partitions, major 259) and `/dev/nfsb-*`
(linear dm devices, major 253).

## NFSB header field map

All 32-bit fields are **big-endian**. Values are the live `fs1` header.

| Offset | Field | Value | Use |
| :--- | :--- | ---: | :--- |
| `0x04` | version | 3 | |
| `0x05` | verity version | 1 | first field of the verity params |
| `0x06` | start sector | 8 | `linear` start (`8 * 512 = 0x1000`) |
| `0x0a` | data length (sectors) | 38080 | verity target length |
| `0x12` | data block count | 4760 | `num_data_blocks` |
| `0x16` | data block size | 4096 | `data_block_size` |
| `0x2a` | hash block size | 4096 | `hash_block_size` |
| `0x1a` | hash algorithm | `sha256` | ASCII |
| `0x2e` | salt | 64 hex chars | ASCII |
| `0x6f` | root digest | 64 hex chars | ASCII |
| `0xb0` | RSA signature | 256 bytes | `nfsb_verify` |

`hash_start_block` is computed, not stored:
`hash_start = (header[0x0a] * 512) / header[0x2a]`. For `fs1` that is `4760`,
so the hash tree starts immediately after the 4760 data blocks.

## Verified run

A read-only loop copy of `fs1` (`/dev/loop0`, 61440 sectors) was used; the live
rootfs and `/dev/nfsb-*` were not touched.

| Step | Result |
| :--- | :--- |
| `nvt_dm_setup_linear` | returned 1; linear `dev_t` `253:10` |
| `nvt_dm_setup_nfsb` | returned 1; verity `dev_t` `253:11`; out `/dev/mapper/loop0` |
| Nodes | `/dev/linear-6` -> loop `7:0`; `/dev/nfsb-6` -> linear `253:10`; `/dev/mapper/loop0` -> verity `253:11` |
| dmesg | `dm: target linear of size 61432 on 253:10 is ready`; `dm: target verity of size 38080 on 253:11 is ready` |
| `mount -t squashfs -o ro /dev/mapper/loop0` | rc 0; read the stock rootfs (`bin`, `etc/init.d/S21idtv.sh`, ...) |
| `umount` | rc 0 |

The dmesg lines match the boot-time NFSB mount exactly, which is the proof that
the reversed ABI and field mapping are the runtime path.

## Rollback

- `reboot -f`; the loop copy and the dm devices are RAM state.
- After boot: same kernel, `ndp_logo` seloff module, policy export
  `b43297b1…`, `/dev/mapper` back to the live set, `/dev/linear-6` and
  `/dev/mapper/loop0` gone, `fs1` header `NFSB`, vendor `/swdl/autorun.upg`
  unchanged.

## What this unlocks and what remains

- The runtime NFSB dm chain is now fully reproduced from userspace through the
  carrier. The header check is patchable (doc 38) and the mapping is known.
- A **modified data block now verifies** after the tree is recomputed and the
  header root digest at `0x6f` is replaced; the control (stock tree/digest)
  still returns EIO. See
  [the dm-verity data path](44-nfsb-verity-data-path-2026-11-22.md). Because
  `nvt_dm_setup_nfsb` reads the digest and salt from the header, the rebuilt
  tree is what dm-verity enforces.
- A bootable modified NFSB is **not** unlocked. The boot-time verifier and
  dm-verity run before Linux, so a boot image still needs the Phase R recovery
  path or a boot-chain verifier bypass.

## Limits

- Lab-only, hardware-only. Do not run the carrier or these calls on a field
  unit.
- The mapping is reversed from the shipped kernel text; a firmware change can
  move the functions or the header layout.
- The verity device is read-only in this test. The modified-data mount is the
  next gate and is not yet claimed.

## Evidence

[2026-11-22 NFSB dm mapping](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-22-nfsb-dm-mapping.md).

## Related

- [NFSB mount-path verifier](40-nfsb-mount-check-2026-11-20.md)
- [dm-verity data path](44-nfsb-verity-data-path-2026-11-22.md)
- [Runtime verifier patch](38-runtime-verifier-patch-2026-11-20.md)
- [Level 3.5 carrier](37-kernel-carrier-level-3-5.md)
- [Runtime NFSB raw SquashFS mount](17-runtime-nfsb-squashfs.md)
- [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md)
