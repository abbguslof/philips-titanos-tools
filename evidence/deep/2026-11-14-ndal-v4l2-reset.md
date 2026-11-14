# 2026-11-14 NDAL V4L2 reset and the paused-appmgr eburner retry

Status: **TESTED-NEGATIVE** for the paused-`appmgr` eburner retry.
**VERIFIED static** for the NDAL V4L2 functions and the exact reset control.
**OPEN** for the helper and the eburner script.

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
through the reset did not make the eburner enter; the STBC/AC trigger is the
unreliable step.

## Libraries

| Library | Size | SHA-256 |
| :--- | ---: | :--- |
| `libNDAL_EX.so` | 342,952 | `4aef83c18735efd0384dc48b3acad9e8b3b3f6427429e603585a2b466434a9fd` |
| `libNDAL3.so` | 389,924 | `72dee768432711acf7335e96fb34b38f4033d27788a769dc1b934638d9703b2d` |
| `libdev.so` | 704,204 | `32923fd8f605981ae77e78a297f3b58d6e319e5d546a1c6356b9edd3a66c83b9` |

`libNDAL_EX.so` NEEDED: `libasound.so.2`, `libNDAL3.so`, `libstdc++.so.6`,
`libm.so.6`, `libgcc_s.so.1`, `libc.so.6`. It imports `v4l2_open` and
`v4l2_ioctl`; the pulled libraries do not provide them.

## Functions

| Function | Address | Evidence |
| :--- | ---: | :--- |
| `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` | `0xb6ad1` | `libplat.so` reset wrapper |
| `NDAL_VideoExt_STBC_ResetByHWWDT` | `0x137f0` | `libNDAL_EX.so` |
| `NDAL_VideoExt_STBC_ResetByHWWDT_WithPowerOnEventACON` | `0x13854` | Builds two controls, `config_ctrllist`, `ioctl` |
| `ndcommon_v4l2_config_ctrl` | `0x27554` | Fills `[0]=id`, `[4]=count`, `[8]=0`, `[12]=value` |
| `ndcommon_v4l2_config_ctrllist` | `0x27534` | Fills the list `which`/`count`/controls |
| `ndcommon_v4l2_ioctl` | `0x27574` | `v4l2_ioctl(gfd_v4l2, cmd, arg)`; returns 1 unless `-1` |
| `ndcommon_v4l2_set_fd` | `0x275d4` | Sets `gfd_v4l2` |
| `Hal_VideoDec_v4l2_set_ctrls` | `0x278d0` | `VIDIOC_S_CTRL` (`0xc008561c`) on `ctrl+0x10` |

V4L2 data: `/dev/video%i` at `0x2ca54`; `gv4l2_dev_name` at `0x2cbd0`;
`gfd_v4l2` at `0x50d98`; `gv4l2_dev_open` at `0x51f2c`/`0x52354` in
`libNDAL_EX.so`; `gv4l2_dev_index` at `0x38938`, `g_v4l2_fd` at `0x56608`, and
`g_v4l2_fd_common` at `0x6c68c` in `libNDAL3.so`.

## Exact reset call

```text
config_ctrl(id=0xf17f1f, ctrl1, value=0, count=1)
config_ctrl(id=0xf17f1f, ctrl2, value=1, count=1)
config_ctrllist(which=0x0f170000, list, ctrl1, count=2)
ioctl(0xc0185647, list)
```

Neighbouring controls: `0xf17f26` (`SetMcuWoLOnOff`), `0xf17f27`
(`SetMcuWoWOnOff`), `0xf17f2c` (`SetMcuFakeSTROnOff`); those use
`0xc0185648`. The `0xc0185648`/`0xc0185647` pair is `S_EXT_CTRLS`/`G_EXT_CTRLS`
with the vendor class.

## Cleanup and live state

| Item | Value |
| :--- | :--- |
| p9 `misc` | `c32f354f0d4869a0c53b6f66eb1dc6b4dcc80293d6bbdbc32a740e917a857f39` |
| p9 `0x3e00` | Zero / original `_ALL_EU_NT72690_…` block |
| Vendor `/swdl/autorun.upg` | `74d2790adda5252d4761eafac33fa7c38017a6666a49a06f861e11cc35cce817`, 917,372,175 bytes |
| `autorun_size.txt` | `917372175` |
| `autorun_version.txt` | `940186113` |
| STBC mode | Off, ioctl `0xc0105310`, struct `00 00 00 00 c9 00 00 00 c9 00 00 00 00 00 00 00` |
| Boot areas | `eee415…` on both |
| `appmgr` | `com.nvt.appmgr` PID 645 running |

The TV boots normally. The test made no boot-area or eMMC writes.

## Redaction

This page contains sizes, hashes, offsets, symbol names, and addresses only. It
does not contain raw vendor payloads, private keys, serial numbers, MAC
addresses, SSIDs, or credentials.
