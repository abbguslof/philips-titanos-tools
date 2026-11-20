# 2026-11-20 kernel carrier (Level 3.5)

Status: **VERIFIED (hardware)** for the carrier build, load, sysfs parameter,
KCFI set/get, self-buffer write/read, symbol resolution, and safe reads.
**VERIFIED (hardware)** for rollback and warm reboot. The direct verifier
patch is in
[2026-11-20 runtime verifier patch](2026-11-20-runtime-verifier-patch.md).
**OPEN** for the NFSB mount integration and hardware-control payloads.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [research/37](../../docs/research/37-kernel-carrier-level-3-5.md).

Kernel addresses are omitted. Resolve them live with `tools/carrier_ctl.py sym`.

## Build

| Item | Value |
| :--- | :--- |
| Vendor module | `a4ca05ce8cdb5163c0004a7ce780d8f482c866edba4745b4d5d20eae869c8985` |
| Carrier module (initial) | `99b7df0324c9d2e6cd412aadf10c60760fc20fbb266c990cc218504dd8b76eaf` |
| Carrier module (512-byte scratch) | `76f09b62ad4039322ca8eacdb1485c8a634329a94fb38a85929678eb0c6acd31` |
| KCFI probe | vendor `ndp_logo_ioctl` and clang agree on `0xe01408cd` |
| Init/cleanup | `mov w0,#0; ret` (vendor driver init skipped) |
| Parameter | `/sys/module/ndp_logo/parameters/carrier`, mode `0644` |

The build used the `ndp_logo.ko` pulled from the TV, not a cached copy.

## Load

`rmmod ndp_logo` returned 0 from the seloff module. `insmod` of the carrier
returned 0. The module line was:

```text
ndp_logo 28672 0 - Live <carrier-va> (O)
```

`/sys/module/ndp_logo/parameters/carrier` existed with mode `-rw-r--r--`.
The kernel logged no carrier error.

## Self-test

`tools/carrier_ctl.py selftest` ran the probe, obtained the carrier scratch
address, wrote a marker to that buffer, and read it back:

```text
carrier selftest ok: probe=0x0d15ea5e0d15ea5e buf=<carrier-va> read=0xcafebabedeadbeef
```

This exercises the KCFI-checked `set` and `get` calls and the 64-bit write and
read on the carrier's own writable buffer.

## Symbol resolution and reads

| Symbol | Result |
| :--- | :--- |
| `selinux_state` | `0x0101000101010000` |
| `nfsb_verify` first 8 bytes | `0xd10343fff800865e` (`str x30, [x18], #8; sub sp, sp, #0x50`) |
| `nvt_dm_check_nfsb` first 8 bytes | `0xd10183fff800865e` (`str x30, [x18], #8; sub sp, sp, #0x60`) |
| `set_memory_rw` | resolved |
| `set_memory_ro` | resolved |
| `aarch64_insn_patch_text_nosync` | resolved |
| `copy_from_kernel_nofault` | resolved |
| `flush_icache_range` | absent |

## KCFI cross-check

The live `param_ops_int` structure held `set` and `get` pointers. The 4 bytes
before each pointer were:

| Target | Word before the function |
| :--- | :--- |
| `param_ops_int.set` | `0x63fa7f9c` |
| `param_ops_int.get` | `0xc64c3dfc` |

Both match the carrier's compiled `carrier_set` and `carrier_get` prefixes.
The live kernel accepts the carrier's type hashes.

## Nofault guard

A safe read of the unmapped `0xffffffc000000000` returned
`0xfffffffffffffff2` (EFAULT). The module stayed live. Direct reads of
unmapped addresses remain unsafe; use `safe-read`.

## Rollback and reboot

`rmmod ndp_logo` returned 0. Re-inserting
`/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko` returned 0 and restored the seloff
module (`ndp_logo 24576 0 - Live`). The parameter directory disappeared.

After `reboot -f`:

- `uid=0(root)` on SSH, uptime 125 s.
- `ndp_logo` was the seloff module, not the carrier.
- `/tmp/ndp_logo_carrier.ko` was gone (tmpfs cleared).
- `getenforce` printed `Enforcing`; the loaded policy hash was
  `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`.
- `customer_env.sh` still loaded `ndp_logo_seloff_boot.ko` unless
  `no_kernel_module` exists.

A second load, self-test, and rollback run on the same day used the initial
carrier. The later 512-byte scratch build (`76f09b62...`) also loaded and
passed the probe; the runtime verifier patch evidence covers that build.

## Limits

- The direct `nfsb_verify` patch is in
  [2026-11-20 runtime verifier patch](2026-11-20-runtime-verifier-patch.md).
  The NFSB mount integration remains open.
- `aarch64_insn_patch_text_nosync` handles the mapping and icache;
  `set_memory_rw` is the fallback.
- The carrier is non-persistent and stayed out of the boot hook.
- The parameter is world-readable. The last result can leak a kernel address.
- No boot-chain, boot-area, or eMMC access.
