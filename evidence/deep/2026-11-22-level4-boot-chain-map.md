# 2026-11-22 Level 4 boot-chain map (read-only)

Status: **READ-ONLY MAP**. No boot-area, eMMC, or FDT writes.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: `tools/bootchain_dump.py` (read-only) and static analysis of
`libfwup.so`. Raw images stay under the gitignored `dist/` tree; this summary
records hashes and structure only.

## Live A/B hashes

| Item | SHA-256 |
| :--- | :--- |
| `boot0` (active XBoot) | `1c74949e2cef6ee67b4f3b477d795f7c111697d4e3951f8eb24982b85a8d993d` |
| `boot1` (recovery XBoot) | `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd` |
| `p1` (U-Boot slot 0) | `e7698f8f509074edad327ef26a13e97d2baa60624d43abb685d3b04faa8388b4` |
| `p2` (U-Boot slot 1) | `756355f8f105d48a6fef07e62ae1dc29b7ad114386955f58abaef844030255b5` |
| `p9` (slot map) | `7e8fca3d37187a48b061565d42f68df9039df595e7c7c3eaac087cfa0872fec9` |
| `p19` NFSB header (active rootfs) | `49f81af35652990f77e5896c75b018113705e52383ac0bc13a40377ff7d1bc47` |
| `p20` NFSB header (recovery rootfs) | `e6aa38507b71059da266c8d010764e1fd66fe8cd043496a9d9abb53ad4f17659` |
| VTBL (`p1`/`p2` `0xe7ee00`) | `2e4575e4705e40d0…` |

## Findings

- `p1` and `p2` are byte-identical to the pre-update dumps. The only
  differences are `0x1a0034` (STBC slot) and `0x1a0204` (UMFG slot).
- The VTBL is identical in `p1` and `p2` and identical to the pre-update VTBL.
- The NVHC map at `p9` `0x1200`/`0x2400` is identical to the pre-update map:
  11 entries of `0x4c` bytes, static `xboot` field `8135df38…`.
- `p19` changed (active rootfs slot 0); `p20` is the old recovery rootfs.
- `boot0`/`boot1` differ in 371,968 bytes across 2,807 runs after a shared
  16-byte header. The XBoot is encrypted.
- Secure component uImages carry a 260-byte trailer after the data; the
  partition tail after the trailer is zero. The stored uImage data is
  high-entropy.

## App-layer switch

`nvt_emmc_set_boot_part_id(path, part)` accepts 1/2, sets EXT_CSD
`PARTITION_CONFIG` (`0xb3`) bits `[5:3]`, and writes it with `MMC_IOC_CMD`
`0xc048b300`, CMD6 opcode 6, flags `0x49d`.
`nvtfw_enable_secure_boot` (`0x6d3c`) is `movs r0,#1; bx lr`;
`nvtfw_process_vtbl_cb` returns success without VTBL work when it is 0.

## Limits

- Read-only. The A/B switch, corrupted-image restore, and any modified
  boot-area write are not tested.
- The VTBL AES keys do not directly decrypt the VTBL body to stored-component
  hashes; the table's consumer and the XBoot/trailer keys remain open.
- Raw boot images and device identifiers are not published.
