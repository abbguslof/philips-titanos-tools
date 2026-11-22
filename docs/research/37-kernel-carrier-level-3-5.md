# Level 3.5: reusable kernel carrier (Phase K)

Status: **VERIFIED (hardware) 2026-11-20** for the build, load, parameter,
KCFI set/get, self-buffer write/read, symbol resolution, safe reads, rollback,
reboot, and the direct `nfsb_verify` patch. The mount-path check, the `ndp_led`
backlight, and the full `linear` + `verity` dm mapping are verified in
[39](39-ndp-led-pwm-backlight-2026-11-20.md),
[40](40-nfsb-mount-check-2026-11-20.md), and
[43](43-nfsb-dm-mapping-2026-11-22.md). The dm-verity data path is verified in
[44](44-nfsb-verity-data-path-2026-11-22.md). No boot-chain, boot-area, or eMMC
writes.

This page closes Phase K from the
[deep jailbreak roadmap](25-deep-jailbreak-roadmap.md). The carrier builds from
the TV's own `ndp_logo.ko`, loads, exposes the parameter, passes the live KCFI
check, and reads and writes kernel memory. The first payload, a direct
`nfsb_verify` patch, is verified in
[38](38-runtime-verifier-patch-2026-11-20.md). The full NFSB dm mapping is
verified in [43](43-nfsb-dm-mapping-2026-11-22.md).

## Why

The `ndp_logo` seloff carrier proved unsigned kernel code execution and an
arbitrary kernel write, but it is a one-shot payload: hardcoded target, no
usable interface, and the module init/cleanup were hand-patched. Level 3.5
needs a repeatable primitive:

- no hardcoded module base or symbol offsets;
- symbol addresses resolved at run time (`/proc/kallsyms`);
- controlled 64-bit kernel read/write and a kernel call;
- reversible, non-persistent, and crash-recoverable.

The carrier does not make a modified boot image bootable. It is the runtime
layer that can inspect and patch verifiers without touching the boot chain.

## Design

`tools/build_carrier.py` merges a small freestanding object into the shipped
`ndp_logo.ko` with `ld.lld -r`. The module keeps its identity:

| Item | Kept |
| :--- | :--- |
| `.gnu.linkonce.this_module` (name, vermagic, license) | vendor bytes |
| `__versions` symbol CRCs | vendor table, unchanged |
| `.modinfo` | vendor bytes |
| `.init.text` / `.exit.text` | vendor sections |
| Undefined symbols | exactly the vendor set |

The only additions are:

- `/sys/module/ndp_logo/parameters/carrier` (mode `0644`), a string mailbox;
- `carrier_set` / `carrier_get` in `.text`;
- a 32-byte `kernel_param_ops` and a 40-byte `kernel_param`;
- `carrier_raw_call` in a separate translation unit;
- a 512-byte scratch buffer for `a`/`m` and the `scratch`/`poke` helpers.

`init_module` and `cleanup_module` are replaced with `mov w0,#0; ret`, so the
logo driver is **not** initialised. This matches the current seloff carrier,
which also skips the driver init. `--keep-driver-init` keeps the vendor
init/cleanup for a variant that needs the driver.

### KCFI and the shadow call stack

The kernel is built with KCFI (type hashes in front of indirect-call targets)
and the shadow call stack. The carrier handles both:

- `carrier_set` and `carrier_get` are compiled with `-fsanitize=kcfi`, so
  clang emits the KCFI hash for their exact prototypes. The kernel's
  `param_attr_store` / `param_attr_show` indirect calls check that hash.
- `carrier_raw_call` is a separate translation unit compiled **without**
  KCFI, so the arbitrary function call is not type-checked. It is the only
  place that calls an unknown prototype.
- The build compiles a probe with the vendor ioctl prototype
  (`long(struct file*, unsigned int, unsigned long)`) and compares clang's
  hash with the vendor `ndp_logo_ioctl` prefix. A mismatch stops the build.
  On the tested toolchain (clang 23.1.3, LLD 21.0.0) the hashes match
  `0xe01408cd`.
- The entry patch keeps the vendor KCFI word and the shadow-stack push stays
  skipped consistently: `mov w0,#0; ret` never pushes, so it never pops.

### Protocol

Write one command as a string to the parameter; read the parameter to get the
last result as `0x%016x`.

| Command | Meaning |
| :--- | :--- |
| `n` | set the result to `0x0d15ea5e0d15ea5e` (probe) |
| `r <addr>` | read 64 bits by direct dereference |
| `w <addr> <value>` | write 64 bits by direct dereference |
| `c <addr> <a0>..<a5>` | call a kernel address with up to six arguments |
| `a` | set the result to the address of the 512-byte scratch buffer |
| `m` | set the result to the first word of the scratch buffer |

`<addr>`, `<value>` and call arguments are hexadecimal. The `c` command passes
integer/pointer arguments only and returns the `x0` register; a 32-bit
function's upper bits are not meaningful. The parameter is world-readable and
root-writable; the last value can leak a kernel address to a local reader.
That is acceptable on the rooted lab and matches `kptr_restrict=0`.

## Build

Requirements: clang with an aarch64 backend, a compatible `ld.lld`, and the
vendor `ndp_logo.ko` for the firmware under test. The tool never downloads
firmware.

```bash
cd philips-titan-tools
python3 tools/build_carrier.py \
  --module /path/to/ndp_logo.ko \
  --output dist/carrier/ndp_logo_carrier.ko
```

`dist/` is gitignored. On the tested host the build is reproducible:

```text
vendor  a4ca05ce8cdb5163c0004a7ce780d8f482c866edba4745b4d5d20eae869c8985
output  76f09b62ad4039322ca8eacdb1485c8a634329a94fb38a85929678eb0c6acd31
kcfi    vendor/clang 0xe01408cd
```

The first carrier build, before the 512-byte scratch buffer, was
`99b7df03...`. The buffer change produced `76f09b62...`. Both load and pass the
probe.

The build refuses to write output if:

- a required section is missing;
- the merged module gains or loses an undefined symbol;
- the carrier parameter is not `0644` or its ops relocation is not
  `carrier_ops`;
- the KCFI probe does not match the vendor `ndp_logo_ioctl` hash;
- the init/cleanup entry patch overlaps a relocation.

Offline checks:

```bash
python3 tests/test_build_carrier.py -v
PHILIPS_NDP_LOGO_KO=/path/to/ndp_logo.ko \
  python3 tests/test_build_carrier.py -v
```

## Live proof (2026-11-20)

The build used the `ndp_logo.ko` pulled from the TV. `insmod` returned 0. The
module line was `ndp_logo 28672 0 - Live <carrier-va> (O)`, and
`/sys/module/ndp_logo/parameters/carrier` existed with mode `0644`.

`tools/carrier_ctl.py selftest` ran the probe, obtained the scratch address,
wrote a marker to that word, and read it back:

```text
carrier selftest ok: probe=0x0d15ea5e0d15ea5e buf=<carrier-va> read=0xcafebabedeadbeef
```

Live reads and the nofault guard:

| Target | Result |
| :--- | :--- |
| `selinux_state` | `0x0101000101010000` |
| `nfsb_verify` first 8 bytes | `0xd10343fff800865e` |
| `nvt_dm_check_nfsb` first 8 bytes | `0xd10183fff800865e` |
| unmapped `0xffffffc000000000` via `safe-read` | EFAULT (`0xfffffffffffffff2`), module stayed live |

The live `param_ops_int` structure held `set` and `get` pointers. The 4 bytes
before each pointer were `0x63fa7f9c` and `0xc64c3dfc`, matching the carrier's
compiled `carrier_set` and `carrier_get` prefixes. The live kernel accepts the
carrier's type hashes.

The direct verifier patch is in
[38](38-runtime-verifier-patch-2026-11-20.md): the carrier holds a real NFSB
header in its scratch buffer, `nfsb_verify` returns 0 for the pristine header
and `0xffffbf00` for a modified signature, and the two-instruction patch makes
the modified header return 0. Reboot restores the original
`0xd10343fff800865e`.

`flush_icache_range` was absent. `aarch64_insn_patch_text_nosync`,
`set_memory_rw`, and `set_memory_ro` were present.

Rollback and reboot:

- `rmmod ndp_logo` returned 0.
- Re-inserting `/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko` returned 0 and
  restored the seloff module. The parameter directory disappeared.
- After `reboot -f`, root returned with the seloff module loaded, the policy
  hash `b43297b16436980131e5ebb2c6b5f883d292a7947eb2d233b2fc08d051cffdc2`, and
  no `/tmp/ndp_logo_carrier.ko`.

Evidence: [2026-11-20 kernel carrier](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-20-kernel-carrier.md).

## Live runbook (owned lab only)

Keep the USB autoroot stick and the 2026-11-14 eMMC backup available. One
change, one test, one rollback. This runbook ran on 2026-11-20; the live proof
above records the result.

1. Confirm state: `tools/carrier_ctl.py --host <TV_IP> status`.
2. Copy the carrier to `/tmp` with
   `ssh -p 2222 root@<TV_IP> 'cat > /tmp/ndp_logo_carrier.ko' < dist/carrier/ndp_logo_carrier.ko`.
   Dropbear on this unit has no `sftp-server`, so plain `scp` fails.
3. If `ndp_logo` is the current seloff carrier, `rmmod ndp_logo`. If it is in
   use, create `/mtd_rwarea/apdat/no_kernel_module` and cold boot, then load
   the carrier manually. Do **not** change the boot hook yet.
4. `insmod /tmp/ndp_logo_carrier.ko`; confirm
   `/sys/module/ndp_logo/parameters/carrier` exists.
5. `tools/carrier_ctl.py --host <TV_IP> probe` must print
   `carrier ok: 0x0d15ea5e0d15ea5e`. Then
   `tools/carrier_ctl.py --host <TV_IP> selftest` must print the probe, scratch
   address, and marker.
6. Resolve and read:
   `carrier_ctl.py --host <TV_IP> sym selinux_state nfsb_verify`,
   `carrier_ctl.py --host <TV_IP> safe-read selinux_state`.
7. Roll back: `rmmod ndp_logo`, then re-insert
   `/mtd_rwarea/apdat/ndp_logo_seloff_boot.ko` or reboot. The carrier is not in
   the boot hook, so the reboot returns to the seloff path.

A bad address can fault the kernel. If SSH stops answering, unplug AC for
about 10 seconds; the root hook and permissive policy are independent of this
module.

## Level 3.5 primitives

| Primitive | How |
| :--- | :--- |
| Symbol resolution | `carrier_ctl.py sym <name>` reads `/proc/kallsyms` as root. |
| Safe read | `carrier_ctl.py safe-read <name>` calls `copy_from_kernel_nofault` into the carrier scratch buffer, then `m`. |
| Dump | `carrier_ctl.py dump <name-or-0xaddr> --length N` reads through `copy_from_kernel_nofault`. |
| Raw read | `carrier_ctl.py read <name-or-0xaddr>`. |
| Raw write | `carrier_ctl.py --yes write <name-or-0xaddr> <value>`. |
| Kernel call | `carrier_ctl.py --yes call <name-or-0xaddr> [args...]`. |
| Scratch | `carrier_ctl.py scratch` prints the 512-byte buffer address. |
| Poke | `carrier_ctl.py --yes poke <name-or-0xaddr> --from-file PATH` writes local bytes to a kernel address. |

The first text-patch experiment is a runtime verifier bypass, not a boot write.
`aarch64_insn_patch_text_nosync` is present on this unit and handles the page
mapping and instruction cache. `flush_icache_range` is absent. Resolve the
addresses first, then patch one 32-bit instruction at a time:

```bash
# 1. Confirm the helpers and targets.
carrier_ctl.py --host <TV_IP> sym \
  aarch64_insn_patch_text_nosync set_memory_rw set_memory_ro \
  copy_from_kernel_nofault nfsb_verify nvt_dm_check_nfsb

# 2. Patch mov w0,#0; ret.
carrier_ctl.py --host <TV_IP> --yes call \
  aarch64_insn_patch_text_nosync 0x<nfsb_verify> 0x52800000
carrier_ctl.py --host <TV_IP> --yes call \
  aarch64_insn_patch_text_nosync 0x<nfsb_verify+4> 0xd65f03c0

# 3. Verify the first 8 bytes.
carrier_ctl.py --host <TV_IP> safe-read nfsb_verify
# expect 0xd65f03c052800000
```

Fallback: call `set_memory_rw` on the page, `write` the 8-byte word
`0xd65f03c052800000`, then call `set_memory_ro`. This unit has no
`flush_icache_range`, so the fallback relies on a reboot or another cache
flush. Test the patch on a copy of an NFSB image under `/mtd_tmpdat`, not the
live rootfs, and reboot to undo it.

This direct sequence is verified for `nfsb_verify` in
[38](38-runtime-verifier-patch-2026-11-20.md). The runtime mount-path check is
verified in [40](40-nfsb-mount-check-2026-11-20.md), and the full
`linear` + `verity` dm mapping in [43](43-nfsb-dm-mapping-2026-11-22.md).

## Limits and open items

- **Full NFSB dm mapping verified.** `nvt_dm_setup_linear` and
  `nvt_dm_setup_nfsb` build the `linear` and `verity` targets, and a loop copy
  mounts the stock SquashFS read-only. See
  [43](43-nfsb-dm-mapping-2026-11-22.md). Use a loop copy; do not touch the live
  rootfs or `/dev/nfsb-*`.
- **Hardware control verified for the backlight.** See
  [39](39-ndp-led-pwm-backlight-2026-11-20.md). HDMI, Ambilight, and tuner
  remain open.
- **dm-verity data path verified.** A modified data block verifies after the
  tree is recomputed and the header root digest is replaced; the stock
  tree/digest still returns EIO. See
  [44](44-nfsb-verity-data-path-2026-11-22.md). The raw SquashFS mount remains
  the working path for modified userspace.
- `aarch64_insn_patch_text_nosync`, `set_memory_rw`, `set_memory_ro`, and
  `copy_from_kernel_nofault` are present. `flush_icache_range` is absent.
- Direct `read`/`write` is unsafe on an unmapped address. Use `safe-read` where
  possible. Writes have no fault guard.
- The world-readable parameter exposes the last result. Do not leave the
  carrier loaded outside an experiment.
- The carrier is a runtime layer. It does not change `NVHC`, `lnikauth`,
  dm-verity, or the signed boot chain, and it does not make a modified NFSB or
  kernel bootable.
- The build uses the clang/lld on the host. A future compiler whose KCFI hash
  changes is rejected before output.

## Related

- [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md)
- [Runtime verifier patch](38-runtime-verifier-patch-2026-11-20.md)
- [Kernel, module, and hardware control surfaces](16-kernel-and-hardware-control.md)
- [SELinux runtime control](15-selinux-runtime-control.md)
- [Runtime NFSB bypass](17-runtime-nfsb-squashfs.md)
- [App-layer update gate](31-app-update-gate-2026-11-14.md)
