# 2026-11-14 NDAL V4L2 reset and the eburner retries

Status: **TESTED-NEGATIVE** for the paused-`appmgr` retry, the script after
the full AC-on wrapper, and the p9-metadata entry attempts. **VERIFIED static**
for the NDAL V4L2 functions, the control layout, the `/dev/video24` target, the
classic eburner USB-image initramfs, and the p9 metadata layout. **OPEN** for
the eburner entry trigger and the `sys_run` script.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`.

Method and discussion: [research/32](../../docs/research/32-ndal-v4l2-reset-2026-11-14.md).

## Paused-appmgr retry

| Artifact | Value / result |
| :--- | :--- |
| Package | `b51cd228f01c7ca6f1cd2047e92e67a5960809da75f75a7eda346d65825ed9b8`, 27,759,995 bytes |
| `appmgr` | `com.nvt.appmgr` PID 636 stopped with `kill -STOP` |
| p9 flag | `PKG_ready/swdl/autorun.upg` at `misc + 0x3e00` |
| STBC mode | On, ioctl `0xc0105310`, 16-byte struct `00 00 00 00 c9 01 00 00 c9 00 00 00 00 00 00 00` |
| AC cycle | Package survived; p9 `0x4000` zero; no `/swdl/eburner-proof.txt`; eburner did not enter |
| Package after | Intact until the app layer removed it after `appmgr` resumed |
| Boot areas | `eee415012095a8c51be032d1e713ac120211408aeebe029b8791526bbe4d30bd` |

The app layer removed the package after `appmgr` resumed. Keeping the package
through the reset did not make the eburner enter; the STBC/AC trigger was the
unreliable step.

## Libraries

| Library | Size | SHA-256 |
| :--- | ---: | :--- |
| `libNDAL_EX.so` | 342,952 | `4aef83c18735efd0384dc48b3acad9e8b3b3f6427429e603585a2b466434a9fd` |
| `libNDAL3.so` | 389,924 | `72dee768432711acf7335e96fb34b38f4033d27788a769dc1b934638d9703b2d` |
| `libdev.so` | 704,204 | `32923fd8f605981ae77e78a297f3b58d6e319e5d546a1c6356b9edd3a66c83b9` |
| `libv4l2.so.0` | 79,912 | `9e95381abb565ec0aca356b16e9341ca53eafd54206a6cb1f64fa68dee8ff0a9` |

`libNDAL_EX.so` NEEDED: `libasound.so.2`, `libNDAL3.so`, `libstdc++.so.6`,
`libm.so.6`, `libgcc_s.so.1`, `libc.so.6`. It imports `v4l2_open` and
`v4l2_ioctl`; `libv4l2.so.0` provides them and needs
`libv4lconvert.so.0`.

## Functions

| Function | Address | Evidence |
| :--- | ---: | :--- |
| `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` | `0xb6ad1` | `libplat.so`; panel sequence + NDAL reset |
| `NDAL_VideoExt_STBC_ResetByHWWDT` | `0x137f0` | `libNDAL_EX.so`; one control, `G_EXT_CTRLS` |
| `NDAL_VideoExt_STBC_ResetByHWWDT_WithPowerOnEventACON` | `0x13854` | Builds two controls, `config_ctrllist`, `ioctl` |
| `NDAL_VideoExt_OpenDevice` | `0x1279c` | Opens `/dev/video%i`, sets `gfd` |
| `ndcommon_v4l2_config_ctrl` | `0x27554` | Fills one 20-byte control |
| `ndcommon_v4l2_config_ctrllist` | `0x27534` | Fills the list `which`/`count`/controls |
| `ndcommon_v4l2_ioctl` | `0x27574` | `v4l2_ioctl(gfd, cmd, arg)`; returns 1 unless `-1` |
| `ndcommon_v4l2_set_fd` | `0x275d4` | Sets `gfd` at `0x50d90` |
| `Hal_VideoDec_v4l2_set_ctrls` | `0x278d0` | `VIDIOC_S_CTRL` (`0xc008561c`) on `ctrl+0x10` |

`nm -D libNDAL_EX.so` confirms the four `ndcommon_v4l2_*` symbols are defined
(`T`) in that library; the odd `0x27535`/`0x27555`/`0x27575`/`0x275d5` forms are
the Thumb-bit addresses of the even entries in the table.

## V4L2 data

| Global / data | Address | Meaning |
| :--- | ---: | :--- |
| `/dev/video%i` | `0x2ca54` | path format |
| `gv4l2_dev_name` | `0x2cbd0` | 7-byte index table `14 18 15 1c 0e 42 00` |
| `gfd` | `0x50d90` | fd used by `set_fd` and `ndcommon_v4l2_ioctl` |
| `gfd_v4l2` | `0x50d98` | separate 24-byte object |
| `gv4l2_dev_open` | `0x51f2c`/`0x52354` | per-index open flags |
| `gv4l2_dev_index` (`libNDAL3.so`) | `0x38938` | live device index |
| `g_v4l2_fd` (`libNDAL3.so`) | `0x56608` | fd |
| `g_v4l2_fd_common` (`libNDAL3.so`) | `0x6c68c` | common fd |

The index table maps to `/dev/video20`, `/dev/video24`, `/dev/video21`,
`/dev/video28`, `/dev/video14`, and `/dev/video66` (sys names
`ndp_av_atv_scart_extin`, `ndp_comp_extin`, `ndp-hdmi`, `ndp-hdmi-switch`,
`imvq-mfc-dec4`, and `ndp_vga_extin`). `NDAL_VideoExt_OpenDevice(0, 0xA)`
selects index 1 -> `/dev/video24`. The live `framework-daemon` has `gfd` = 61
and fd 61 -> `/dev/video24`; the helper's `open_dev(0, 0xA)` also opened
`/dev/video24`.

## Exact reset call

```text
config_ctrl(id=0x0f170f1f, ctrl1, value=0, size=1)
config_ctrl(id=0x0f170f1f, ctrl2, value=1, size=1)
config_ctrllist(which=0x0f170000, list, ctrl1, count=2)
ioctl(0xc0185647, list)
```

| Field | Value |
| :--- | :--- |
| control id | `0x0f170f1f` (AC-on); `0x0f170f29` (plain) |
| class/`which` | `0x0f170000` |
| ioctl | `0xc0185647` (`G_EXT_CTRLS`) |
| control stride | `0x14` (20 bytes) |
| control layout | `[0]=id`, `[4]=size`, `[8]=0`, `[0xc]=value pointer`, `[0x10]=0` |
| list layout | `[0]=which`, `[4]=count`, `[8]=error_idx`, `[0xc]/[0x10]=reserved`, `[0x14]=controls pointer` |
| value | one byte, pointer to `0` then `1` |

The earlier entry wrote `0xf17f1f` and 16-byte controls; the disassembly shows
`0x0f170f1f`, a 20-byte stride, and a value pointer. The neighbouring setters
(`0xf17f26`, `0xf17f27`, `0xf17f2c`) use the `S_EXT_CTRLS` side `0xc0185648`.

## Helper test

A local 32-bit ARM helper used the TV's glibc 2.36 and `dlopen`:

1. `libnpc.so` (typeinfo), `libv4lconvert.so.0`, `libv4l2.so.0`
2. `libNDAL_EX.so`, `libplat.so`, `libutlt.so`, `libdev.so`

Data stubs supplied for `bplatCECIsSemiOrStandby`, `g_b8MutexUnlockChecked`,
`g_b8MutexChecked`, `g_pstUtiliMemCheckQueueHandle`, `g_b8MemChecked`,
`gu8DebugFuncLevelControl`, and `g_b8MemProtectFlag`. The helper called
`NDAL_VideoExt_OpenDevice(0, 0xA)` and then
`PLAT_SYS_ResetByHWWDT_PowerOnEventACOn()`.

| Test | Package before | Reset result | Package after | p9 `0x3e00` | p9 `0x4000` | Proof |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Raw `G_EXT_CTRLS` on `/dev/video24` | `b51cd228…` | TV reset | intact | `PKG_ready` | zero | absent |
| Full `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` | `b51cd228…` | TV reset | **removed** | `PKG_ready` | zero | absent |

The full wrapper is the stronger trigger: it consumed `/swdl/autorun.upg` and
the app layer removed the remainder after reboot. It still did not produce
`/swdl/eburner-proof.txt`, `PKG_SUCCESS`, or an `EBURN_START`/`EBURN_PROOF`
marker. The boot areas were unchanged. The remaining blocker is the eburner
loader/package extraction or the `sys_run` format, not the reset trigger.

Local helper log (no secrets):

```text
helper2: start
OK   libnpc.so
OK   libv4lconvert.so.0
OK   libv4l2.so.0
OK   libNDAL_EX.so
OK   libplat.so
OK   libutlt.so
OK   libdev.so
helper2: open_dev=... reset=...
helper2: open_dev fd=4
helper2: fd3 -> /swdl/v4l2-helper2.log
helper2: calling reset
```

The log ends at `calling reset`; the wrapper reset the TV. The `fd3` is the log
file in that run; the opened video node was fd 4. The independent live check is
`gfd` = 61 -> `/dev/video24`.

## Eburner initramfs and p9 metadata

`eburner` component: `02-eburner.img`, u-boot uImage, Linux ARM64 5.4.254,
22,566,920 payload bytes. The gzip cpio initramfs is at component offset
`0xfd8948`; it contains `etc/init.d/S21eburner.sh`,
`bin/nvt_extract_sys_run`, `bin/nvt_eburner`, and busybox.

`S21eburner.sh` uses a USB image, not `/swdl`:

```text
IMAGE_PATH=nvt_tv_firmware.img
parse /proc/cmdline for nvt_eburner_img=*
wait for /dev/sda1 and /media/sda1/${IMAGE_PATH}
nvt_ctrl_adc_reset disable
nvt_extract_sys_run ${UPDATE_FNAME}
/tmp/sys_run/run.sh ${UPDATE_FNAME}
```

Live/package p9 metadata:

| Offset | Live p9 | Package component |
| ---: | :--- | :--- |
| `0x400` | `PPCH` pptbl0 | `pptbl0` (1536 B, exact) |
| `0xa00` | `PPCH` pptbl1 | `pptbl1` (1536 B, exact) |
| `0x1000` | `FWVR` vinfo | `vinfo` (512 B, exact) |
| `0x3600` | `UPST` factory status | `upst` (512 B, update status) |
| `0x3800` | zeros | `bflag` (`BTFG`, 512 B; offset inferred) |
| `0x3e00` | `_ALL_EU_…` / `PKG_ready` | app `SetPKGFlag` |

`libfwup.so`: `nvtfw_get_bflag` `0x6dbc`, `nvtfw_emmc_read_pptbl` `0x7d48`,
`nvtfw_emmc_write_pptbl` `0x7ea8`, `nvtfw_emmc_sync_dbflag_boot_part`
`0xa75c`, `BTFG` `0x198e0`. `nvtfw_emmc_write_pptbl` writes a 0x600-byte PPCH
table at a block offset.

STBC: `DEV_UART_Set_SWEburnerOnOff` (libdev `0x49dec`) opens `/dev/ntkstbc`
O_RDWR, ioctl `0xc0105310`, 16-byte struct `00 00 00 00 c9 <arg> 00 00 c9 ...`.
`APP_MGR_SYS_Reset` -> `PLAT_SYS_Reset` (`libplat` `0xb2ee8`, normal reboot);
`...PowerOnEventACOnForUpgrade` -> the HWWDT wrapper (`0xb6ad0`).

Additional tests:

| Test | `/swdl` | USB image | p9 metadata | Result |
| :--- | :--- | :--- | :--- | :--- |
| HWWDT, p9 `/swdl`, no USB | consumed | none | live | reset; no script |
| HWWDT/normal reset, p9 `/swdl` + USB p9 | intact/consumed | p9 | live | no script |
| HWWDT/reset, p9 `/swdl` + USB full | intact | full `ccba5334…` | live | no script |
| `PLAT_SYS_Reset`, p9 `/swdl` + USB full | intact | full | live | helper blocked; no reset |
| HWWDT/reset, p9 `/swdl` + USB full | intact | full | `UPST` 0x3600, `BTFG` 0x3800, `PKG_ready` 0x3e00 | no script |

The full USB package `dumponly.pkg` (`ccba5334…`, 1.53 GB) was verified and
left intact; no `update-proof.txt` appeared. The p9 metadata writes persisted
and were reverted. The eburner entry trigger remains open.

## Next

- Capture the eburner serial console (`ttyS0`, 115200; the TV TX is alive) to
  see whether the eburner boots and why the USB image is not used.
- Or analyze the bootloader/NVM eburner-selection flag; the app-layer flow sets
  the STBC mode, p9 `PKG_ready`, and p9 `bflag`/`upst` before `PLAT_SYS_Reset`.
- Verify the USB mount path/label and `nvt_eburner_img=`.

## Cleanup and live state

| Item | Value |
| :--- | :--- |
| p9 `misc` | `c32f354f0d4869a0c53b6f66eb1dc6b4dcc80293d6bbdbc32a740e917a857f39` |
| p9 metadata | `UPST`/`BTFG` writes reverted with the pristine p9 restore |
| p9 `0x3e00` | Zero / original `_ALL_EU_NT72690_…` block |
| Vendor `/swdl/autorun.upg` | `74d2790adda5252d4761eafac33fa7c38017a6666a49a06f861e11cc35cce817`, 917,372,175 bytes |
| `autorun_size.txt` | `917372175` |
| `autorun_version.txt` | `940186113` |
| USB image | `nvt_tv_firmware.img` removed after the test |
| STBC mode | Off, ioctl `0xc0105310`, struct `00 00 00 00 c9 00 00 00 c9 00 00 00 00 00 00 00` |
| Boot areas | `eee415…` on both |
| `appmgr` | `com.nvt.appmgr` running |

The TV boots normally. The test made no boot-area or eMMC writes.

## Redaction

This page contains sizes, hashes, offsets, symbol names, and addresses only. It
does not contain raw vendor payloads, private keys, serial numbers, MAC
addresses, SSIDs, or credentials.
