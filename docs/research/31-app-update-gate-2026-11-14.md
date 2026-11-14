# App-layer update gate: `/swdl` trigger and RSA verification

Status: **VERIFIED (hardware)** for the genuine VER40 USB update and A/B
activation. **VERIFIED (static)** for the trigger, verifier, classic eburner
USB-image initramfs, and p9 metadata. **OPEN** for the modified VER40
package/RSA bypass and the classic eburner entry.

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

1. **Direct `/swdl` staging with root (app-layer path).** Copy a local package
   to `/swdl/autorun.upg`, set the eburner flag, and reset. This skips the
   app-layer `StartSoftwareUpdate` and its RSA check. The update environment's
   own check is open. The `nvt_eburner` whole-image verifier is MD5-only
   and accepts `TIMG`; the `eburner` kernel and the loader may check more.
2. **Runtime patch of `libfwup.so`.** Patch `nvtfw_sec_verify_whole_img_sign`
   to return 0, or `nvtfw_enable_secure_boot` to return 0, and bind-mount the
   patched library over `/mtd_apexe/board/lib/libfwup.so` at boot. This would
   let the app layer accept a modified VER40 package. The update environment's
   check is open.
3. **Vendor private key.** Not present in `libfwup.so` or the app partition.
   The PEM markers are not a key. Signing a modified package from the app layer
   is not possible.

## Direct staging flag path

The root-only `/swdl` path needs a package and two flag writes:

| Step | Function | Address | Effect |
| :--- | :--- | ---: | :--- |
| Package | `APP_MGR_SWUpdate_USB_StartSoftwareUpdate` | `0x27dd89` | Copies the package to `/swdl/autorun.upg`. |
| Flag | `APP_MGR_SWUpdate_Cust_SetPKGFlag` | `0x789d5` | Writes `PKG_ready<path>` at `misc + 0x3e00` (0x90 bytes). |
| Mode | `DEV_UART_Set_SWEburnerOnOff` | `0x49ded` | Opens the UART/STBC device and issues ioctl `0xc0105310` with arg 0. |
| Status | `MID_SWUpdate_USB_SetEburnerStatus` | `0x98555` | No-op in this build. |

`libdev.so` SHA-256 `32923fd8f605981ae77e78a297f3b58d6e319e5d546a1c6356b9edd3a66c83b9`.
The `/dev` strings include `/dev/ntkstbc`, `/dev/ntgpio`, `/dev/ntkiic0`, and
`/dev/ttyS2`. `research/32` confirms `/dev/ntkstbc`, the ioctl, and the
struct. The eburner kernel carries `nvt_soc_stbc_in_eburn_mode` and the
`## EBURN ## flow-1/flow-2` messages. It does not carry a package-signature
string.

The direct staging test:

1. Back up `/swdl/autorun.upg` and `p9` (`misc`).
2. Copy the classic dump-only package to `/swdl/autorun.upg`.
3. Write `PKG_ready/swdl/autorun.upg` at `misc + 0x3e00`, padded to 0x90 bytes.
4. Set the STBC eburner mode with ioctl `0xc0105310`.
5. Reset. The eburner should run `sys_run/run.sh`.
6. The script writes `update-proof.txt` and the two boot-area images to the
   USB, hashes `/dev/mmcblk0` read-only, and reboots.

The classic eburner extraction path is mapped in
[research/32](32-ndal-v4l2-reset-2026-11-14.md): its initramfs reads a USB
image at `/media/sda1/nvt_tv_firmware.img`, extracts `sys_run`, and runs
`/tmp/sys_run/run.sh`. The `/swdl` staging steps above exercise the app-layer
path; they do not feed the classic eburner. The `nvt_eburner` verifier is
MD5-only; the `run.sh` skips it. The package signature gate is bypassed
because the package is staged directly, not through the app-layer verifier.

## Next

- The vendor VER40 USB update is proven: genuine package, active slot 0,
  AC-on activation, version `002.236.191`; root/persistence survived; recovery
  pair slot 1/boot1.
- Next: patch `libfwup` RSA (`nvtfw_sec_verify_whole_img_sign` `0xb889` or
  `nvtfw_enable_secure_boot` `0x6d3d`) and the app-layer version check; build a
  modified VER40 component; keep the old pair recovery.
- The classic eburner USB-image path remains open; the serial console is the
  diagnostic if that route continues.
- Do not test on field units.

## Direct staging test (2026-11-14)

Two AC-on cycles entered the eburner with the STBC eburner mode, the
`PKG_ready` flag, and a classic package. The eburner consumed
`/swdl/autorun.upg`; the screen went black and the TV rebooted to the normal
dashboard. The `run.sh` left neither `PKG_SUCCESS` nor
`/swdl/eburner-proof.txt`. The app layer restored the vendor
`/swdl/autorun.upg` (917 MB) on the next boot.

The trimmed package (`pre_install`, `part_tbl`, `eburner`, `sys_run`) was the
first candidate; the p9 metadata (`vinfo`, `upst`, `bflag`, `pptbl0/1`) was
mapped later in [research/32](32-ndal-v4l2-reset-2026-11-14.md). The classic
eburner reads the USB image, so the `/swdl` package did not feed its `run.sh`.
A diagnostic package with `EBURN_START` at the top of `run.sh` did not enter on
its AC cycles; the AC trigger was not repeatable after the STBC off/on
sequence.

The vendor AC-on reset through `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` /
`NDAL_VideoExt_STBC_ResetByHWWDT_WithPowerOnEventACON` was attempted through
`gdbserver` on `idtv`. The LAN port is firewalled; the SSH tunnel found the
gdbserver gone; the gdbserver killed `idtv` and `appmgr` restarted. The UI
needs a power cycle. The gdb path is not usable as-is. A dynamic helper
replaced it; see [research/32](32-ndal-v4l2-reset-2026-11-14.md).

### Paused-appmgr retry (2026-11-14)

A third retry staged the p9 package (`b51cd228…`) and stopped `com.nvt.appmgr`
(PID 636) with `kill -STOP` so the app layer could not remove the package. The
package survived the AC cycle, but the eburner did not enter:
`misc + 0x3e00` stayed `PKG_ready/swdl/autorun.upg`, `misc + 0x4000` was zero,
`/swdl/eburner-proof.txt` was absent, and the boot areas were unchanged.
Keeping the package through the reset did not fix the STBC/AC entry.

The cleanup restored the vendor `/swdl` package, the p9 `misc`, and the STBC
mode. The NDAL V4L2 reset route is in
[research/32](32-ndal-v4l2-reset-2026-11-14.md).

### Full AC-on wrapper test (2026-11-14)

A local helper called `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` after
`NDAL_VideoExt_OpenDevice(0, 0xA)`. The wrapper reset the TV; one run left
`/swdl/autorun.upg` removed and later runs left it in place. The p9 flag stayed
`PKG_ready`, `misc + 0x4000` was zero, `/swdl/eburner-proof.txt` was absent,
and the boot areas were unchanged. The raw V4L2 `G_EXT_CTRLS` alone reset the
TV and left the package. The cleanup restored the vendor package, the p9
`misc`, and the STBC mode.

The classic eburner initramfs (extracted from the `eburner` component) reads a
USB image at `/media/sda1/nvt_tv_firmware.img`, not `/swdl/autorun.upg`; it
extracts `sys_run` and runs `/tmp/sys_run/run.sh`. The app-layer `VER40` path
and its `/swdl` flag are a separate flow. A full classic package on the USB,
plus the p9 `UPST`/`BTFG` metadata, did not enter in the tested reset
sequences; the entry trigger remains open. See
[research/32](32-ndal-v4l2-reset-2026-11-14.md).

## Vendor VER40 USB update (2026-11-14)

The app-layer USB update accepted the genuine `TIMGPKGVER40` package. The TV
menu listed the package only after it was renamed to `autorun.upg`; the
original `.pkg` name was ignored. It loaded, validated, and programmed active
slot 0 (`p15`/`p17`/`p19`). The TV rebooted to the old slot. An AC-on cycle
then activated slot 0: firmware `002.236.191`.

| Partition | Active slot 0 | Recovery slot 1 |
| :--- | :--- | :--- |
| FDT | `p15` `9ac6c6de…` | `p16` `7d7535e9…` |
| kernel | `p17` `85dd1e43…` | `p18` `c6be43cf…` |
| rootfs | `p19` `4c267420…` | `p20` `2dbca39e…` |

The eMMC boot area changed too: boot0 `1c74949e…` (new), boot1
`eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd` (old).
The active boot part is 1; the recovery boot1 is the other part. `p9` changed
to `7e8fca3d…`; `p1`/`p2`, `p13`/`p14`, and `p21` are unchanged. The live
`/swdl/autorun.upg` is the vendor `74d2790a…` package.

The serial log showed `PowerOnEvt:AC ON(2)`, `switched:0`, `dual_all_same:0`,
`addon_stats=2`, `boot_area:1`, and `lnikauth pass`. Root and persistence
survived: `uid=0`, dropbear `:2222`, telnetd `:2323`, `customer_env.sh`, and
freetitan.

The app-layer RSA verifier is now the barrier for a modified package. The next
step is a patched `libfwup` plus a modified VER40 component; the recovery pair
is slot 1/boot1. The app-layer version check may also need a patch.

## Safety

- The probe made no boot-area or eMMC writes. The direct staging wrote `/swdl`
  and the p9 flag, and set the STBC mode; the cleanup restored the p9 flag,
  turned off the STBC, and restored the vendor `/swdl/autorun.upg`
  (`74d2790a…`) and the p9 `misc` (`c32f354f…`) on 2026-11-14. The boot areas
  are unchanged.
- The local package, `/swdl` package, and libraries stay out of the repo.
- This note publishes no key material.
