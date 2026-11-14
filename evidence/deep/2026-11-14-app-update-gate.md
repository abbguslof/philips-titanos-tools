# 2026-11-14 app-layer update gate

Status: **VERIFIED static**. No TV writes. The update environment's own check
and the eburner flag mapping are **OPEN**.

Target: `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`.

The method and discussion are in
[app-layer update gate](../../docs/research/31-app-update-gate-2026-11-14.md).

## Libraries

| Library | Size | SHA-256 |
| :--- | ---: | :--- |
| `libapp.so` | 5,678,304 | `16f6543cca628bc57d4ee7eba4da72e152cbbcfecbaac41337eabfdeb8955e20` |
| `libmid.so` | 1,961,288 | `7e23d1ef1ef76b0beab224dd47c3a8c348d208cbf428865d6ce6eab09fc5fd4e` |
| `libfwup.so` | 152,220 | `2f260407609cc5b209b6c3890ea5acd2880721df7355725c391a928d68874989` |
| `libmgr_cust.so` | 1,680,744 | `056a2a0589a2812e5d150e11c914e0a27c400745901c12cb141d8941e29c2acc` |
| `libdev.so` | 704,204 | `32923fd8f605981ae77e78a297f3b58d6e319e5d546a1c6356b9edd3a66c83b9` |

## Trigger

| Function | Address | Evidence |
| :--- | ---: | :--- |
| `APP_MGR_SWUpdate_USB_StartSoftwareUpdate` | `0x27dd89` | Builds `cp %s /swdl/autorun.upg`, runs `system()`, calls `MGR_Softwareupdate_Start()`. |
| `APP_MGR_SWUpdate_USB_SetEburnerUpdate` | `0x27dec1` | `DEV_UART_Set_SWEburnerOnOff()`, `APP_MGR_SWUpdate_USB_SetEburnerStatus(1)`, `APP_MGR_SWUpdate_Cust_SetPKGFlag()`, `APP_MGR_SYS_Reset()`. |
| `APP_MGR_SWUpdate_USB_SoftwareVerify` | `0x27dc85` | `APP_MGR_SWUpdate_ChkUPGAndLocalSWVersion()`, then `MID_Swupdate_USB_VerifyFile()`. |
| `APP_MGR_SWUpdate_USB_CheckPKGUpgradeByFileName` | `0x27eabd` | USB package selection. |

## Verification chain

| Function | Address | Evidence |
| :--- | ---: | :--- |
| `MID_Swupdate_USB_VerifyFile` | `0x9a061` | Queues `MID_SWUPDLIB_CMD_FUNC_USB_VERIFYFILE` (command 8). |
| `_MID_Swupdate_USB_VerifyFile` | `0x9846d` | Calls `_MID_Swupdate_VerifyFile`; logs `Start normal upgrade VerifyFile`, `verify success!`, `verify failed!`. |
| `_MID_Swupdate_VerifyFile` | `0x9836d` | Opens the package and calls `nvtfw_verify_whole_image()`. |
| `nvtfw_enable_secure_boot` | `0x6d3d` | Returns 1. |
| `nvtfw_verify_whole_image` | `0x6e7d` | `TIMG` at 0x00, `PKGVER40` at 0x04; MD5 path only if secure boot is off; otherwise calls `nvtfw_sec_verify_whole_img_sign`. |
| `nvtfw_sec_verify_whole_img_sign` | `0xb889` | 0x100-byte signature at header offset 0x1c; `mbedtls_pk_parse_public_key`; `mbedtls_pk_verify`. |

Relevant strings: `Only support PKGVER40`, `image sum check error!`,
`verify fail!`, `Start normal upgrade VerifyFile,FilePath = %s`.

## Key material

- Private-key markers at file offsets `0x1bd88` (END) and `0x1bda8` (BEGIN).
  The END marker precedes the BEGIN marker and no key block exists between
  them.
- Public-key markers at `0x1bdc8` (END) and `0x1bde4` (BEGIN). Same layout.
- The verifier uses an embedded public key. No private key material is
  published or present in the library.
- `vtbl_soft_key`, `vtbl_soft_key_aes256`, `vtbl_key_patt`, and
  `vtbl_key_patt_aes256` are in `.data` at `0x2d468`–`0x2d4a8`. They are AES
  keys/patterns for the VTBL path. Their values are not published.

## Live `/swdl` package

```text
path       /swdl/autorun.upg
size       917,372,175 bytes
md5        74e9ca9362fb2c4ccf4757283ee4bfca
magic      TIMGPKGVER40 (offset 0x00)
size file  917372175
version    940186113
```

The local classic package is `TIMG` with 0x488 PIMG headers and is not accepted
by the app-layer verifier, which requires `PKGVER40`.

## Eburner flag path

| Function | Address | Effect |
| :--- | ---: | :--- |
| `APP_MGR_SWUpdate_Cust_SetPKGFlag` | `0x789d5` | Writes `PKG_ready<path>` at `misc + 0x3e00` (0x90 bytes). |
| `DEV_UART_Set_SWEburnerOnOff` | `0x49ded` | Opens a UART/STBC device and issues ioctl `0xc0105310` with arg 0. |
| `MID_SWUpdate_USB_SetEburnerStatus` | `0x98555` | No-op in this build. |

`libdev.so` SHA-256 `32923fd8…`. The `/dev` strings include `/dev/ntkstbc`,
`/dev/ntgpio`, `/dev/ntkiic0`, and `/dev/ttyS2`; the STBC device is inferred.
The eburner kernel carries `nvt_soc_stbc_in_eburn_mode` and `## EBURN ##
flow-1/flow-2`; it has no package-signature string.

Direct staging plan: back up `/swdl/autorun.upg` and `p9`; copy the classic
dump-only package to `/swdl/autorun.upg`; write
`PKG_ready/swdl/autorun.upg` at `misc + 0x3e00`; set the STBC eburner mode;
reset. Not tested.

## Bypass options

1. Direct `/swdl` staging with root: copy a classic package to
   `/swdl/autorun.upg`, set the eburner flag and STBC mode, reset. The
   app-layer RSA check is skipped; the update environment check is open.
2. Runtime patch `libfwup.so`: patch `nvtfw_sec_verify_whole_img_sign` or
   `nvtfw_enable_secure_boot`, bind-mount the patched library at boot. The
   update environment check is open.
3. Vendor private key: not present. The PEM markers are not a key.

## Direct staging test (2026-11-14)

| Artifact | Result |
| :--- | :--- |
| Classic trimmed package `ccba5334…` | Staged; two AC-on cycles entered the eburner; package consumed; no proof, no `PKG_SUCCESS`. |
| Fast `/swdl` proof package `b45c1ecb…` | Staged; eburner consumed it; no `/swdl/eburner-proof.txt`, no `PKG_SUCCESS`. |
| Diagnostic `EBURN_START` package `a2ee050b…` | Staged; AC cycles did not enter the eburner; p9 stayed `PKG_ready`; package later removed by the app layer. |
| Vendor restore | `/swdl/autorun.upg` back to 917,372,175 B, SHA-256 `74d2790a…`, size/version `917372175` / `940186113`. |
| p9 | Restored to the original SHA-256 `c32f354f…`; flag at `0x3e00` original (no `PKG_ready`). |
| Boot areas | `eee415…` on both. |
| STBC | `DEV_UART_Set_SWEburnerOnOff` off (`c9 00`); eburner mode cleared. |

The eburner entered and consumed the classic packages, but the user-space
`run.sh` did not leave the proof or `PKG_SUCCESS`. The app layer restored the
vendor package. The trimmed package likely lacks loader-required p9 metadata
(`vinfo`, `upst`, `bflag`, `pptbl0/1`); the `insmod`, `/swdl` mount, and `$BB`
path are also candidates.

The `gdbserver`/gdb vendor reset attempt failed: the LAN port is firewalled,
the SSH tunnel found the gdbserver gone, and the gdbserver killed `idtv`.
`appmgr` restarted; the UI needs a power cycle. No boot-area or eMMC writes
were made; the p9 flag and STBC were restored.

## Redaction

This page contains sizes, hashes, offsets, symbol names, and addresses only. It
does not contain raw vendor payloads, private keys, serial numbers, MAC
addresses, SSIDs, or credentials.
