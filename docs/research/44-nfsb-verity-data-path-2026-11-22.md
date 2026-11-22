# dm-verity data path: a modified block that verifies

Status: **VERIFIED (hardware) 2026-11-22** for a modified data block passing
dm-verity after a recomputed hash tree and an updated header root digest, over a
loop copy. A custom NFSB image is minted and mounted read-only in
[45](45-custom-nfsb-mount-2026-11-22.md). **OPEN** for a bootable modified NFSB
(Level 4).

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [full NFSB dm mapping](43-nfsb-dm-mapping-2026-11-22.md) and the
[verifier patch](38-runtime-verifier-patch-2026-11-20.md).

## Why

Doc 43 proved the `linear` + `verity` mapping with stock data. Doc 17 showed a
modified block failing dm-verity. The remaining gate was the data path: can a
modified block be made to verify?

## Hash tree

The stock `fs1` image defines the format:

- data block size 4096, hash block size 4096, `sha256`, 32-byte digest, salt
  from the header at `0x2e` (32 bytes), root digest at `0x6f` (64 hex chars);
- 4760 data blocks, so level 0 has `ceil(4760 / 128) = 38` hash blocks;
- level 0: `H(salt || data_block)` for each block, packed into 4096-byte hash
  blocks, last block zero-padded;
- higher levels: `H(salt || hash_block)` for each hash block, until one block
  remains;
- root = `H(salt || top_block)`.

On-disk layout (**verified against the stock image**): the tree starts at
`hash_start_block` with the highest level first, then each lower level, ending
with the level 0 blocks. The stock tree occupies 39 blocks (1 top + 38 level 0)
at `0x1000 + 4760 * 4096`.

Recomputing the tree from the stock data reproduces the header digest
`6bdf03ba…`, which fixes the algorithm and layout.

## Modified image

- Copy the stock `fs1` image.
- Overwrite linear block 100 with a marker (`MODIFIED-DATA-PATH-2026-11-22`),
  leaving the squashfs data otherwise unchanged.
- Recompute the tree and write it at `hash_start_block`.
- Replace the ASCII root digest at `0x6f` with the recomputed root.
- Keep the salt and every other header field.

The control keeps the stock tree and stock digest over the same modified data.

Reproduce the tree work with the local tool:

```sh
python3 tools/nfsb_verity.py verify fs1.img
python3 tools/nfsb_verity.py rebuild modified.img --output rebuilt.img
```

## Results

Both mappings were built with `nvt_dm_setup_linear` + `nvt_dm_setup_nfsb` on
separate read-only loop copies.

| Case | Tree / digest | Read block 100 | Read block 101 |
| :--- | :--- | :--- | :--- |
| Control | stock / stock | **EIO**; dmesg `data block 100 is corrupted` | OK |
| Rebuilt | recomputed / recomputed | **OK**; first bytes `MODIFIED-DATA-PATH-2026-11-22AAA` | OK, identical to control |

- Control: linear `253:10`, verity `253:11`, node `/dev/mapper/loop0`.
- Rebuilt: linear `253:12`, verity `253:13`, node `/dev/mapper/loop1`.
- The rebuild returned exactly the local modified block
  (sha256 `27112b64…`); block 101 was byte-identical in both mappings.

## Rollback

`reboot -f`; the loop copies and dm devices are RAM state. After boot the live
state was intact: same kernel, `ndp_logo` seloff module, policy export
`b43297b1…`, live `/dev/mapper`, `fs1` header `NFSB`, vendor `/swdl/autorun.upg`
`74d2790a…`.

## What this means

- dm-verity is no longer a barrier for a modified NFSB **at runtime** when the
  tree and the header root digest can be rewritten. The header signature check
  is separately bypassable at runtime ([38](38-runtime-verifier-patch-2026-11-20.md),
  [40](40-nfsb-mount-check-2026-11-20.md)).
- This is a RAM-only capability. It does **not** make a modified NFSB bootable:
  the boot-time verifier and dm-verity run before Linux.
- A custom NFSB image is minted and mounted read-only with the same header,
  tree, and mapping. See
  [the custom NFSB mount](45-custom-nfsb-mount-2026-11-22.md). The raw verity
  read remains the data-path proof.

## Limits and safety

- Lab-only, hardware-only. Use a loop copy; do not touch the live rootfs or
  `/dev/nfsb-*`.
- The proof is a raw block read through the verity device, not a mounted
  modified SquashFS.
- A modified boot image still needs the Phase R recovery path or a boot-chain
  verifier bypass.

## Evidence

[2026-11-22 NFSB verity data path](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-22-nfsb-verity-data-path.md).

## Related

- [Custom NFSB mount](45-custom-nfsb-mount-2026-11-22.md)
- [Full NFSB dm mapping](43-nfsb-dm-mapping-2026-11-22.md)
- [NFSB mount-path verifier](40-nfsb-mount-check-2026-11-20.md)
- [Runtime verifier patch](38-runtime-verifier-patch-2026-11-20.md)
- [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md)
