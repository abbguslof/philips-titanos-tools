# Level 4 boot-chain map and recovery gate

Status: **READ-ONLY MAP / PLAN (2026-11-22)**. The A/B pair, the static
NVHC/VTBL/U-Boot slots, the encrypted XBoot pair, the component trailers, and
the app-layer A/B boot-part switch are mapped. This note carries a correction:
the live boot was slot 1/boot1, not slot 0. The update wrote slot 0 but did not
license it. The A/B switch to slot 0 is **TESTED-NEGATIVE** in
[48](48-ab-switch-failure-2026-11-22.md). No modified boot-area write.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: live read-only dump with `tools/bootchain_dump.py` (2026-11-22) and
static analysis of `libfwup.so`. The pre-update dumps are
`dist/bootchain/2026-11-14/`; the live dump is `dist/bootchain/20261122T121343Z/`.

## Live A/B map

| Item | Written slot 0 (not licensed) | Live boot slot 1 (licensed) |
| :--- | :--- | :--- |
| eMMC boot area | `boot0` `1c74949e…` (new XBoot) | `boot1` `eee41501…` (old XBoot) |
| U-Boot slot | `p1` `e7698f8f…` | `p2` `756355f8…` |
| UMFG slot marker | `0` | `1` |
| VTBL | `2e4575e4…` | `2e4575e4…` (identical) |
| p9 slot map | `7e8fca3d…` (one copy for both) | same |
| Rootfs header | `p19` `49f81af3…` (new) | `p20` `e6aa3850…` (old) |

Key facts:

- `p1` and `p2` are **byte-identical to the pre-update dumps**. The only
  differences are two bytes: `0x1a0034` (STBC slot) and `0x1a0204` (UMFG slot).
  The vendor update did **not** change the U-Boot slots.
- The VTBL is identical in `p1` and `p2` and identical to the pre-update VTBL.
  It is a static structure, not a per-version component hash table.
- `p19` changed (the written slot 0 rootfs); `p20` stayed the old rootfs. The
  live boot was `p20`/slot 1. The update wrote slot 0; it did not boot it.
  [48](48-ab-switch-failure-2026-11-22.md) records the `lnikauth` failure.
- `boot0` and `boot1` differ throughout (371,968 differing bytes, 2,807 runs)
  after a 16-byte shared header. The XBoot is encrypted/obfuscated, not a
  plaintext component.

## NVHC slot map (`p9`)

`NVHC` at `0x1200` (slot 0) and `0x2400` (slot 1), 11 entries of `0x4c` bytes:
`name[8]`, a static 24-byte field, `target[32]`, `flags`, `offset` (512-byte
sectors), `length` (sectors). The map is identical to the pre-update map.

| Name | Target | Flags | Offset | Length |
| :--- | :--- | ---: | ---: | ---: |
| `xboot` | `emmc_boot0/1` | 0 | 0 | `0x300` |
| `uboot` | `boot0/1` | 1 | `0x800` | `0x500` |
| `secos` | `secos0/1` | 1 | 0 | `0x4000` |
| `vertbl` | `boot0/1` | 3 | `0x73f7` | `0x40` |
| `kernel` | `ker0/1` | 1 | 0 | `0xb800` |
| `fdt` | `fdt0/1` | 4 | 0 | `0x1800` |
| `fs` | `fs0/1` | 2 | 0 | 8 |
| `ap` | `apexe0/1` | 2 | 0 | 8 |
| `apext` | `apexe_ext0/1` | 2 | 0 | 8 |
| `stbc_emmc` | `emmc_boot0/1` | 5 | `0xcb800` | `0x104` |
| `bflag` | `misc` | 7 | 0 | 1 |

The `xboot` 24-byte field is static (`8135df38…`) and is **not** the MD5/SHA-1/
SHA-256 of the 384 KiB XBoot region. Treat it as a key/version field, not a
component hash. The `vertbl` entry points at `0xe7ee00` in `p1`/`p2`
(`0x73f7 * 512`), length `0x40` sectors.

## VTBL

`VTBL` at `0xe7ee00` in `p1`/`p2`: magic `VTBL`, length `0x224`, a 32-bit field
`0x7be7d0a3`, then 536 bytes of high-entropy data. The body is not a CRC of the
header and does not directly decrypt with the four `vtbl_*` AES keys in
`libfwup.so` to the stored-component hashes. Keep it as an opaque signed /
protected table until its consumer is reversed.

## XBoot and component protection

- The XBoot pair (`boot0`/`boot1`) is encrypted; the live pair differs
  throughout. The boot ROM/ATF path owns decryption and authentication.
- The secure components are uImages whose stored data is high-entropy (not the
  plaintext the uImage data CRC describes). A **260-byte trailer** follows the
  uImage data; the partition tail after it is zero. The trailer is the
  per-component signature/protection data.
- The kernel/ATF/FDT are therefore encrypted **and** signed. There is no
  private key in the repo or the app-layer libraries.

## App-layer verification surface (`libfwup.so`)

| Symbol | Address | Finding |
| :--- | ---: | :--- |
| `nvtfw_enable_secure_boot` | `0x6d3c` | `movs r0,#1; bx lr` — weak stub returning 1 |
| `nvtfw_process_vtbl_cb` | `0xcaa4` | calls it; if 0, returns success without processing the VTBL |
| `nvtfw_sec_verify_whole_img_sign` | `0xb888` | 0x100-byte signature at header `0x1c`, embedded public key, `mbedtls_pk_verify` (doc 31) |
| `nvtfw_vhash_emmc_vtbl_sha2_cb` | `0xbfec` | VTBL SHA-256 callback |
| `nvt_emmc_set_boot_part_id` | `0xa678` | eMMC boot-part switch (below) |
| `nvtfw_emmc_sync_dbflag_boot_part` | `0xa75c` | reads then sets the boot part to match the dbflag |

`nvtfw_enable_secure_boot` is a concrete **app-layer** bypass point: patching it
to return 0 makes `nvtfw_process_vtbl_cb` a no-op success. It does not affect the
boot ROM or the encrypted XBoot/components.

## A/B boot-part switch

`nvt_emmc_set_boot_part_id(path, part)`:

- accepts `part` 1 (boot0) or 2 (boot1);
- reads EXT_CSD, takes `PARTITION_CONFIG` at index `0xb3`, clears bits `[5:3]`,
  and sets them to `part`;
- opens the eMMC device `O_RDWR`;
- issues `MMC_IOC_CMD` `0xc048b300` with CMD6 (opcode 6), arg
  `0x03b3.. | (part_value << 8)`, flags `0x49d`;
- closes and returns 0.

`nvt_emmc_get_boot_part_id` reads the same field. `nvtfw_emmc_sync_dbflag_boot_part`
wraps get/set; `nvtfw_emmc_read/write_dual_boot_flag` handle the dual-boot flag.

So the switch is explicit: set `PARTITION_CONFIG` bits `[5:3]` to 1/2 and let
the XBoot/U-Boot slot selection follow.

The A/B test set p9 `0x10` = 1 and the boot part to 1, then rebooted. The XBoot
booted boot_area 0 and printed `lnikauth fail`; the boot counter reached
`BC over limit`. The OBR `LONG_PRESS_TO_OBR`/`OBR_SWITCH` did not toggle because
the DB said slot 0. The old slot 1/boot1 stayed intact. The recovery is p9
`0x10` = 2 and `EXT_CSD 0x50`; see
[48](48-ab-switch-failure-2026-11-22.md).

## Barriers

- The boot ROM/ATF decrypts and authenticates the encrypted XBoot; the
  components are encrypted with 260-byte trailers. No key is in userspace.
- The U-Boot slots, VTBL, and NVHC are static across the genuine update. A
  modified U-Boot slot would still need the encrypted-XBoot/component chain to
  accept it.
- The app-layer bypass is real for the update path but does not change the
  boot-time trust.

## Level 4 plan (in order)

1. **Read-only:** pull the live `p13`-`p18` components (or their trailers) and
   map the 260-byte trailer and the XBoot consumer. No writes.
2. **A/B switch:** tested negative. Slot 0 fails `lnikauth`; the old slot
   1/boot1 is the licensed pair. Restore the boot selection to slot 1 (p9
   DBFG 2, `EXT_CSD 0x50`). See
   [48](48-ab-switch-failure-2026-11-22.md).
3. **Corrupted-image restore:** deliberately corrupt the active boot area and
   prove recovery, or prove the boot ROM falls back to boot1. This is the
   documented stop condition for any modified boot-area write.
4. **Only then:** a modified boot-area write (custom XBoot/ATF/kernel/FDT or a
   bootable modified NFSB).

## Open questions

- Does the boot ROM automatically fall back to boot1, or is the boot part an
  explicit EXT_CSD choice only?
- What key/OTP protects the XBoot and the 260-byte component trailers, and can
  it be read or overridden?
- The `lnikauth` check runs in the XBoot. Slot 1/boot1 passes; slot 0/boot0
  fails. The license detail is not in the plaintext artifacts
  (`boot0`/`boot1`/`p1`/`p2`/`p21`).
- Can the app-layer `nvtfw_enable_secure_boot` bypass be combined with the
  update path to write a modified component that the boot ROM still accepts?

## Evidence

[2026-11-22 Level 4 boot-chain map](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-22-level4-boot-chain-map.md).

## Related

- [Recovery engineering](26-recovery-engineering.md)
- [Boot image map](28-boot-image-map.md)
- [App-layer update gate](31-app-update-gate-2026-11-14.md)
- [A/B switch failure](48-ab-switch-failure-2026-11-22.md)
- [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md)
