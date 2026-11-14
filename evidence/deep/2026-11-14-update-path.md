# 2026-11-14 update-path analysis

Status: **VERIFIED** for the local package map and the burner checks.
**INFERRED / OPEN** for the update trigger and the app-layer gate. The
dump-only package is **prepared, not tested**.

Target: `55PUS8000/12`, chassis `TPA256E` / `TPN256E`, firmware
`TPA256E_V056.002.236.191`.

The method and full discussion are in
[update path](../../docs/research/30-update-path-2026-11-14.md). This page
records the hashes, offsets, and addresses that support the claims.

## Package

```text
file            PH_2K25_ALL_EU_NT72690_TPN256E_V056.002.236.191_upgrade.pkg
size            1,530,220,984 bytes
container MD5   6a84824971330f78ac894a8a78698e19
package SHA-256 7b6c7e14298f2845289aeeff500366dcb72be8e748999e44a3244a3a5b2344f3
```

The package is local-only and is not committed.

## Update components

| Name | Header offset | Payload offset | Length | PIMG MD5 | Target |
| :--- | ---: | ---: | ---: | :--- | :--- |
| `pre_install` | `0x120` | `0x5a8` | 512 | `bf619eac0cdf3f68d496ea9344137e8b` | `/dev/null` |
| `part_tbl` | `0x7a8` | `0xc30` | 556 | `eff91c84992b8e2eb5d95201e26e3c00` | `/dev/mmcblk0` |
| `kerupm` | `0x204eeb` | `0x205373` | 19,841,096 | `3f50c56f86e5120444601db8c4f606a8` | `/dev/nvt-part-name/kerupm` |
| `eburner` | `0x19d1b37` | `0x19d1fbf` | 22,566,984 | `fb96e2779b2841e36cf03f847e138f84` | `/dev/null` |
| `sys_run` | `0x2f57807` | `0x2f57c8f` | 5,176,607 | `76eab6c27c9a755f1ed47e7966ffe43c` | `/dev/null` |
| `pptbl0` | `0x47d5f82` | `0x47d640a` | 1,536 | `c7514f300c734d640e01e9d031290506` | `/dev/nvt-part-name/misc` |
| `pptbl1` | `0x47d6a0a` | `0x47d6e92` | 1,536 | `d9ef838465b896ae58e34c4fcb6a6c80` | `/dev/nvt-part-name/misc` |
| `bflag` | `0x47d7492` | `0x47d791a` | 512 | `adc586e8c2b7bdd669d4c1c14ce11b5b` | `/dev/nvt-part-name/misc` |
| `vinfo` | `0x47d7b1a` | `0x47d7fa2` | 512 | `ee08b5a3236d49898246b5cc448750ee` | `/dev/nvt-part-name/misc` |
| `upst` | `0x47d81a2` | `0x47d862a` | 512 | `cda8d5460f1978ffe73170789c56f338` | `/dev/nvt-part-name/misc` |

## `nvt_eburner`

```text
file      nvt_eburner
type      ELF32 ARM EABI5, static, stripped
entry     0x10e11
SHA-256   c517824ad0d8f4fdf3f3e83b8b1d912da732606cf716c432cb5abea737cf2d71
```

Checks:

| Function | Address | Observed check |
| :--- | ---: | :--- |
| `nvt_eburner_verify_whole_image` | `0x11ac4` | `TIMG` magic, 0x120 header, payload hash in 0x800 chunks, 16-byte digest compare. No RSA/SHA. |
| Dual-part burn | `0x11434` | Clears `force_ro` on `mmcblk0boot1`, writes with `dd`, compares `md5sum` of source and destination. |
| `nvt_eburner_gen_md5tbl_in_ram` | `0x16354` | Parses `md5tbl` colon-separated lines into an in-RAM table. |

Strings:

| String | Address |
| :--- | ---: |
| `DUAL-PART-BURN` | `0x99248` |
| `md5sum %s` | `0x992e8` |
| `# md5sum are not same!! (%s=%s, %s=%s)` | `0x9930c` |
| `PKG_SUCCESS` command | `0x99958` |
| `Set boot part failed` | `0x99870` |
| `md5tbl` | `0x9ae4c` |
| `nvt_eburner_verify_whole_image` | `0x9afdc` |

## Live package-to-slot checks

| Component | Live location | Result |
| :--- | :--- | :--- |
| `pptbl0` | `p9 + 0x400` | byte-identical |
| `pptbl1` | `p9 + 0xa00` | byte-identical |
| `vinfo` | `p9 + 0x1000` | byte-identical |
| `upst` | `p9 + 0x3600` | differs (runtime state) |
| `stbc` | `p1/p2 + 0xbb800` | differs (protected/generated) |
| `vtbl` | `p1/p2 + 0xe7ee00` | differs (generated/updated) |
| `bflag` | `p9` | not found byte-identical |
| `kerupm` | `p21 + 0` | byte-identical for 19,841,096 bytes |

`p21` is a plain arm64 uImage with `data_crc=OK`, load/entry `0x02800000`,
data size 19,841,032, SHA-256
`7e2e0733c3bc457ba6f9c5e916a53090682ea1894ddbe0f370b609a42d27f077`.

## Live update trigger state

```text
/swdl/autorun.upg         917,372,175 bytes
/swdl/autorun.upg md5     74e9ca9362fb2c4ccf4757283ee4bfca
/swdl/autorun_size.txt    917372175
/swdl/autorun_version.txt 940186113
```

`p9 + 0x3e10` holds the last package name:

```text
_ALL_EU_NT72690_TPN256E_V056.002.127.021_upgrade.pkg
```

The `p9` name is older than the running `V056.002.236.191` build. The `/swdl`
file has a different size and MD5 from the local package. The exact trigger and
the app-layer RSA check remain open.

## Dump-only package

Built locally from the local package. Only `sys_run` changed.

```text
new sys_run gzip       4,409,897 bytes
padded to              5,176,607 bytes
new sys_run MD5        780e61163ebcb9a6aab0941260544aab
new container MD5      6c0f7326e68e74e469656ad5ef484492
package SHA-256        ccba5334dfb73816cfb616c89d73d6655d4083c2424378fae53b83b747f4f002
```

The new `sys_run` tar contains `run.sh`, `ndp_preinit.ko`, `nvt_eburner`, and
`busybox`. The `run.sh` writes `update-proof.txt` and the two boot-area images
(8 MiB) to the update USB, hashes `/dev/mmcblk0` read-only, and reboots. It
does not call `nvt_eburner` and does not dump the full user area.

The package is in `dist/update-test/` (gitignored) and is not committed. It is
not tested on hardware. The test is blocked on the restore gate.

## Redaction

This page contains sizes, hashes, offsets, and function addresses only. It does
not contain raw vendor payloads, keys, serial numbers, MAC addresses, SSIDs, or
credentials.
