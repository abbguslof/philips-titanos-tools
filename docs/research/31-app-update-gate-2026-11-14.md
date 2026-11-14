# App-layer update gate: `/swdl` trigger and RSA verification

Status: **VERIFIED (static)** for the trigger and the verifier. **OPEN** for
the update environment's own check and the eburner flag mapping. No TV writes.

Target: `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`.

This note corrects the update-path assumption in
[research/30](30-update-path-2026-11-14.md): the app-layer USB update expects a
`TIMGPKGVER40` package. The local 1.53 GB classic package is not valid for that
path. The live `/swdl/autorun.upg` (917,372,175 bytes) starts with
`TIMGPKGVER40`.

## Trigger

`libapp.so` (SHA-256 `16f6543c…`) defines the USB update flow:

| Function | Address | Behaviour |
| :--- | ---: | :--- |
| `APP_MGR_SWUpdate_USB_StartSoftwareUpdate` | `0x27dd89` | Builds `cp %s /swdl/autorun.upg`, runs it with `system()`, then calls `MGR_Softwareupdate_Start()`. |
| `APP_MGR_SWUpdate_USB_SetEburnerUpdate` | `0x27dec1` | Calls `DEV_UART_Set_SWEburnerOnOff()`. On success: `APP_MGR_SWUpdate_USB_SetEburnerStatus(1)`, `APP_MGR_SWUpdate_Cust_SetPKGFlag()`, then `APP_MGR_SYS_Reset()`. |
| `APP_MGR_SWUpdate_USB_SoftwareVerify` | `0x27dc85` | Calls `APP_MGR_SWUpdate_ChkUPGAndLocalSWVersion()`, then `MID_Swupdate_USB_VerifyFile()`. On failure: `MID_Swupdate verify failed`. |
| `APP_MGR_SWUpdate_USB_CheckPKGUpgradeByFileName` | `0x27eabd` | Selects the USB package. |

So the app-layer path is:

```text
USB package -> /swdl/autorun.upg -> verify -> set eburner flag -> reset
```

`libmgr_cust.so` (SHA-256 `056a2a05…`) imports
`APP_MGR_SWUpdate_USB_CheckPKGUpgradeByFileName` and
`APP_MGR_SWUpdate_USB_SetEburnerUpdate`, and holds the `autorun.upg` strings.

## Verification chain

`libmid.so` (SHA-256 `7e23d1ef…`) carries the `libfwupd` task:

| Function | Address | Behaviour |
| :--- | ---: | :--- |
| `MID_Swupdate_USB_VerifyFile` | `0x9a061` | Queues command 8 for the `libfwupd` task. |
| `_MID_Swupdate_USB_VerifyFile` | `0x9846d` | Calls `_MID_Swupdate_VerifyFile`, logs `Start normal upgrade VerifyFile`, `verify success!`, `verify failed!`. |
| `_MID_Swupdate_VerifyFile` | `0x9836d` | Opens the package and calls `nvtfw_verify_whole_image()`. |

`libfwup.so` (SHA-256 `2f260407…`) carries the verifier:

| Function | Address | Behaviour |
| :--- | ---: | :--- |
| `nvtfw_enable_secure_boot` | `0x6d3d` | **Returns 1.** The stub forces the secure path. |
| `nvtfw_verify_whole_image` | `0x6e7d` | Reads the 0x120 header. Requires `TIMG` at 0x00 and `PKGVER40` at 0x04. If secure boot is off, it uses an MD5 whole-image check. With secure boot on, it calls `nvtfw_sec_verify_whole_img_sign`. |
| `nvtfw_sec_verify_whole_img_sign` | `0xb889` | Reads a 0x100-byte signature at header offset 0x1c, parses an embedded public key with `mbedtls_pk_parse_public_key`, hashes the header and payload, and calls `mbedtls_pk_verify`. |

The MD5 path is unreachable on this build because
`nvtfw_enable_secure_boot()` returns 1. The app-layer gate is RSA.

## Key material

- `libfwup.so` contains `-----BEGIN RSA PRIVATE KEY-----` and
  `-----END RSA PRIVATE KEY-----` strings at file offsets `0x1bda8` and
  `0x1bd88`, and matching public-key markers at `0x1bde4` and `0x1bdc8`.
- The markers are separate strings. The END marker precedes the BEGIN marker,
  and there is no base64 key block between them. No private key material is
  present.
- The verifier uses an embedded public key and the RSA verify path. Signing a
  modified package is not possible from this library.
- `libfwup.so` also holds `vtbl_soft_key`, `vtbl_soft_key_aes256`,
  `vtbl_key_patt`, and `vtbl_key_patt_aes256` in `.data`
  (`0x2d468`–`0x2d4a8`). These are AES keys/patterns for the VTBL path. They are
  not published here.

## The live `/swdl` package

```text
/swdl/autorun.upg        917,372,175 bytes, md5 74e9ca9362fb2c4ccf4757283ee4bfca
first bytes              54 49 4d 47 50 4b 47 56 45 52 34 30  = "TIMGPKGVER40"
/swdl/autorun_size.txt   917372175
/swdl/autorun_version.txt 940186113
```

The live package is `TIMGPKGVER40`. The local classic package is not.

## Bypass options

1. **Direct `/swdl` staging with root.** Copy a local package to
   `/swdl/autorun.upg`, set the eburner flag, and reset. This skips the
   app-layer `StartSoftwareUpdate` and its RSA check. The update environment's
   own check is still open. The `nvt_eburner` whole-image verifier is MD5-only
   and accepts `TIMG`; the `eburner` kernel and the loader may check more.
2. **Runtime patch of `libfwup.so`.** Patch `nvtfw_sec_verify_whole_img_sign`
   to return 0, or `nvtfw_enable_secure_boot` to return 0, and bind-mount the
   patched library over `/mtd_apexe/board/lib/libfwup.so` at boot. This would
   let the app layer accept a modified VER40 package. The update environment's
   check is still open.
3. **Vendor private key.** Not present in `libfwup.so` or the app partition.
   The PEM markers are not a key. Signing a modified package from the app layer
   is not possible.

## Next

- Map the eburner flag path: `DEV_UART_Set_SWEburnerOnOff`,
  `APP_MGR_SWUpdate_USB_SetEburnerStatus`, and
  `APP_MGR_SWUpdate_Cust_SetPKGFlag`.
- Map the `eburner` kernel/loader check for a classic `TIMG` package staged at
  `/swdl/autorun.upg`.
- Then test the direct `/swdl` staging with the prepared classic dump-only
  package, after the restore gate and with the USB fallback. The dump-only
  `run.sh` does not write the eMMC.
- Do not test on field units.

## Safety

- No TV writes were made. The analysis used local copies pulled read-only from
  `/mtd_apexe/board/lib` and the `/swdl` header.
- The local package, `/swdl` package, and libraries stay out of the repo.
- No key material is published.
