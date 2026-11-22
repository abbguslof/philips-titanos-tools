# 2026-11-20 NFSB mount-path verifier (Level 3.5)

Status: **VERIFIED (hardware)** for the runtime `nvt_dm_check_nfsb` mount-path
check with a modified loop copy and the patched `nfsb_verify`. The full
`linear` + `verity` dm mapping is verified in
[43](43-nfsb-dm-mapping-2026-11-22.md).

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [runtime verifier patch](38-runtime-verifier-patch-2026-11-20.md) and
[Level 3.5 carrier](37-kernel-carrier-level-3-5.md).

## Why

The direct patch in doc 38 proved the `nfsb_verify` function with a header
buffer. This test uses the runtime mount-path check `nvt_dm_check_nfsb` with a
real block device. The check reads the NFSB header from a path, checks the
magic and version, and calls `nfsb_verify`.

## Method

- Copy the live `fs1` partition to `/tmp/nfsb-loop.bin` (30 MiB).
- Flip the signature byte at `0xb0` from `0x85` to `0x84`.
- Attach the copy with `losetup /dev/loop0`.
- Put `"/dev/loop0"` in the carrier scratch buffer at `buf + 0x1c0`.
- Call `nvt_dm_check_nfsb(buf, path)`.

`nvt_dm_check_nfsb` returns 1 on success and 0 on failure.

## Results

| Case | Return | dmesg |
| :--- | ---: | :--- |
| Unpatched, modified signature | `0` | `nfsb: header verification failed` |
| `aarch64_insn_patch_text_nosync(nfsb_verify, 0x52800000)` | `0` | |
| `aarch64_insn_patch_text_nosync(nfsb_verify + 4, 0xd65f03c0)` | `0` | |
| Patched bytes | | `safe-read` returned `0xd65f03c052800000` |
| Patched, modified signature | `1` | `NFSB header found and verified` |

The patched check accepts the modified header through the real runtime path.

## Rollback and reboot

- `losetup -d /dev/loop0`, remove the copy, unload the carrier, restore the
  seloff module.
- Reboot with `reboot -f`.
- After reboot, `nfsb_verify` returned to `0xd10343fff800865e`.
- Root, the seloff module, and policy
  `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`
  were intact.

## Full mapping

The runtime `linear` + `verity` mapping is reversed and verified with a loop
copy: `nvt_dm_setup_linear` builds the data-area `linear` target and
`nvt_dm_setup_nfsb` builds the `verity` target over it; the verity device mounts
the stock SquashFS read-only. See
[the full NFSB dm mapping](43-nfsb-dm-mapping-2026-11-22.md). The dm-verity data
path (a modified data block) remains open.

## Evidence

[2026-11-20 NFSB mount check](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-20-nfsb-mount-check.md).
