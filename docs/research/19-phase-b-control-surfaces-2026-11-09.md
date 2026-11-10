# Control surfaces (Phase B)

Status: **VERIFIED / OPEN** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-09.

Method: pull the vendor `.ko` from the read-only app partition to the
workstation, read symbols with `readelf`, disassemble the ioctl handler, then
run only non-mutating probes on the device. No guessed request numbers. Every
command number below is either measured from shipped code or marked `UNKNOWN`.

Rules honored: read-only enumeration before any write; one change at a time;
cold boot is the only recovery; no boot-partition access.

## Device map (measured)

| Node | major:minor | sysfs driver | Owner | ioctl ABI |
| :--- | :--- | :--- | :--- | :--- |
| `/dev/ntkmem` | 504:0 | `virtual/ntkmem` | `ndp_misc.ko` (strings + symbols) | measured (below) |
| `/dev/ndp_hwmem` | 10:192 | `virtual/misc/ndp_hwmem` | `UNKNOWN` (not in `ndp_misc`) | `UNKNOWN` |
| `/dev/ntgpio` | 132:0 | `virtual/ntgpio` | `UNKNOWN` (platform) | `UNKNOWN` |
| `/dev/ntkiic0` | 134:0 | `virtual/ntkiic0` | `UNKNOWN` (platform) | `UNKNOWN` |
| `/dev/ntkled` | 503:0 | `virtual/ntkled` | `ndp_led.ko` | handler known, cmds `UNKNOWN` |
| `/dev/ntktcon` | 242:0 | `virtual/ntktcon` | `ndp_tcon.ko` stub / built-in | `UNKNOWN` |
| `/dev/ntkhdmi` | 241:0 | `virtual/ntkhdmi` | `ndp_hdmi.ko` | **standard V4L2** |

Note: `driver/module` symlinks are empty for all seven (platform devices), so
module ownership is inferred from symbols/strings, not sysfs.

### Open-only test (VERIFIED)

All seven opened `O_RDONLY` from the root shell, fd 3, no ioctl:

```
/dev/ntkmem /dev/ndp_hwmem /dev/ntgpio /dev/ntkiic0
/dev/ntkled /dev/ntktcon /dev/ntkhdmi     -> opened O_RDONLY
```

Probe binaries were transferred over HTTP and SHA-256-verified on-device
against the workstation (`ntkctl`, `gpio_enum` hashes match).

## `/dev/ntkmem` = `ndp_misc.ko` (measured)

Module `ndp_misc.ko`, 80,392 bytes,
sha256 `22b944d207803ee23d90ee43bf885c9e1e0d37ee89bab56452b6df400cf269f8`.

`KER_MEM_IOCtl` at `0x2e00`. Entry loads `w1` (the ioctl `cmd`) and compares:

| cmd | Path | Label |
| :--- | :--- | :--- |
| `0x35` | main DDR path: bounds-checks `arg` as a user pointer, `__arch_copy_from_user` of `0x28` (40) bytes, then DDR/MAU test with DMA alloc, `__arch_copy_to_user` back | VERIFIED disasm |
| `0x4d01` | `printk` path | VERIFIED disasm |
| `0x4d02` | `printk` path | VERIFIED disasm |
| other | default `printk` | VERIFIED disasm |

Partial 40-byte struct layout, observed only:

| Off | Use in code | Label |
| ---: | :--- | :--- |
| `0x00` | passed to `__msecs_to_jiffies` (msec/time) | VERIFIED |
| `0x04` | loop/compare length | VERIFIED |
| `0x08` | pattern value written | VERIFIED |
| `0x0c` | flag word gates DMA/test branches; exact bits `UNKNOWN` | VERIFIED field, UNKNOWN bits |
| `0x10..0x27` | `UNKNOWN` | UNKNOWN |

Critical negatives:

- **No `mmap` symbol** in `ndp_misc.ko`; the module exports only ioctl/open/
  release/proc paths. `/dev/ntkmem` is a DDR/MAU test + watchdog interface,
  **not** a general physical-memory window. Label: INFERRED (symbol-set
  evidence; a differently named mmap is not fully excluded).
- Same module contains `_PLAT_WDT_ResetSystem`, `_dbgFunWDTReset`,
  `_dbgFunWDTReset` paths. Reachability from ioctl is `UNKNOWN`; treat any
  unmeasured cmd as capable of resetting the SoC. Do not fuzz.

## `/dev/ntkled` = `ndp_led.ko`

Module `ndp_led.ko`, 445,480 bytes,
sha256 `ed7cb3e749a60c8ae25326f40b988f8f3dd28576908538ff922b9c124dc1dc2f`.

Symbols: `KER_LEDTop_IOCtl`, `KER_LEDTop_CompatIOC`, plus PWM/SPI and
`MAX20096` LED-driver routines (`_dbgFunPWM_SET_DUTY_CH`, `LED_SPI_Write_*`,
`_PWMDIM_SetDuty_CH`, ...). The command constants were **not** extracted yet;
label `UNKNOWN`. Because `_CompatIOC` exists, 32-bit userspace is handled.

Risk: the handler can drive backlight/PWM and LED SPI. A wrong write can blank
the panel (recoverable by cold boot) or disturb the LED driver. Probe only
after extracting the switch and only with a query-type command first.

## `/dev/ntkhdmi` = `ndp_hdmi.ko` (standard V4L2)

Module `ndp_hdmi.ko`, 121,576 bytes,
sha256 `9ede49529afe0d4ae55d54ac5b041312eb5f7685688e05afd4b3a603f7dd6111`.

Symbols are V4L2 ops: `vidioc_querycap`, `vidioc_enum_input`, `vidioc_g_input`,
`vidioc_g_fmt_vid_cap`, `vidioc_g_parm`, `vidioc_g_ext_ctrls`,
`vidioc_s_*`, `vidioc_streamon/off`, plus `compat_video_ioctl2`. So this node
is **not** a vendor ioctl mesh; use standard `VIDIOC_*` numbers. Read-only
queries (`QUERYCAP`, `ENUMINPUT`, `G_INPUT`, `G_FMT`, `G_PARM`) are the safe
first probes. `S_FMT`/`STREAMON` change mode; do not start there. Label:
VERIFIED symbol set; individual results UNKNOWN.

## `/dev/ntgpio` and `gpiochip0`

`/dev/gpiochip0` (label `gpio`) reports **167 lines, all `flags=0`, all with
empty name and empty consumer** (standard v2 lineinfo, read-only). There are
no name hints for standby/power/IR. `/dev/ntgpio` is a separate vendor node
with `UNKNOWN` ABI.

Consequence: GPIO-based power/standby work must first discover line function
by measurement (drive/observe), not by name. That is a write-class action and
is last in the order.

## `/dev/ntktcon`, `/dev/ntkiic0`, `/dev/ndp_hwmem`

- `ndp_tcon.ko` pulled **0 bytes twice**; the node's driver is a platform
  device and tcon is likely built into the kernel image. ABI `UNKNOWN`.
- `ntkiic0` driver is a platform device; standard `/dev/i2c-0..5` also exist.
  Vendor ABI `UNKNOWN`; standard i2c-dev could be used later with a bus map.
- `ndp_hwmem` (10:192) is a misc device, not owned by `ndp_misc`; ABI
  `UNKNOWN`. Whether it maps allocator/CMA memory or arbitrary physical ranges
  is the open question from doc 16 and is **not** answered by ntkmem.

## CDP on `:7788` (VERIFIED)

`/json` returns exactly one page target:

```
494390F3FA1E12BD4A271A12AA672479  page  page_blank.html
file:///mtd_apexe/board/com.nvt.opera/browser_dir/pages/misc/page_blank.html
```

So the webview debug surface is live but currently parked on a blank page, not
the launcher. `Runtime.evaluate` works against that page. This is a debug
surface, not a root path; and it will not drive native `idtv`/Wayland UI.

## Harnesses (built, static armhf)

Source under `tools/probe/`; output under `dist/armhf/`. Target userspace is
ELF class 01 / ARM EABI5 (verified Phase A), so all binaries are 32-bit static.

| Tool | Purpose | Safety |
| :--- | :--- | :--- |
| `ntkctl` | open a `/dev/ntk*` node and (only with `--go`) issue one measured cmd | dry by default; `O_RDONLY` unless `--rw`; buffer capped 4096, zeroed |
| `gpio_enum` | read-only v2 lineinfo of `/dev/gpiochip0` | no line request, no write |
| `uinput_key` | create a virtual kbd and emit one key | cannot touch panel/power/GPIO |
| `cdp.py` | list CDP targets / `Runtime.evaluate` one expression | read-only at call site |

Build:

```sh
sh tools/probe/build.sh        # clang + ld.lld, freestanding, no sysroot
```

Deploy (read path used in this phase):

```sh
# workstation
python3 -m http.server 8000 --bind 0.0.0.0 --directory dist/armhf
# TV
/usr/bin/wget -q -O /tmp/ntkctl http://192.0.2.44:8000/ntkctl
chmod +x /tmp/ntkctl
/tmp/ntkctl /dev/ntkmem none          # open only
```

## Probe order (cannot hang; gates explicit)

| Step | Target | Action | Gate / blocker |
| ---: | :--- | :--- | :--- |
| 0 | all nodes | `ntkctl <dev> none` open-only | done, VERIFIED |
| 1 | `gpiochip0` | `gpio_enum` lineinfo | done, safe |
| 2 | `:7788` | `cdp.py --list`, then `document.title` | done, read-only |
| 3 | `/dev/uinput` | `uinput_key` one key | low risk; **expect inert** (no evdev consumers) |
| 4 | `/dev/ntkmem` | `ntkctl /dev/ntkmem 0x4d01 --go` then `0x4d02` | printk-only paths; **never 0x35 casually** |
| 5 | `/dev/ntkhdmi` | standard V4L2 QUERYCAP/ENUMINPUT/G_FMT | needs a small V4L2 harness (next) |
| 6 | `/dev/ntkled` | extract `KER_LEDTop_IOCtl` switch, then query cmd only | blocked until cmds measured |
| 7 | `/dev/ntktcon` | do not probe | ABI `UNKNOWN`, built-in |
| 8 | `/dev/ntgpio` | discover line function by observation, then write | **last**; power/standby can power off |
| 9 | `/dev/ntkiic0` | only with a bus/target map | **last**; PMIC writes can kill rails |

## What each gives that JointSpace cannot

| Surface | Beyond JointSpace |
| :--- | :--- |
| `uinput` | Kernel-level input injection. JointSpace already sends keys via its API, so likely **no gain** and potentially inert (no evdev consumers). |
| `ntkled`/`ntktcon` | Direct backlight/PWM/panel control (duty, dimming, LED SPI) without appmgr. JointSpace has no backlight/panel API. |
| `:7788` CDP | DOM/JS control of the webview. JointSpace exposes only its REST API; CDP manipulates the actual browser page. |
| `ntgpio` | Raw GPIO read/assert (standby, power-enable, IR). JointSpace can send a power key but cannot read/assert hardware lines. |
| `ntkmem`/`ndp_hwmem` | Kernel/DDR test and (for hwmem) possible allocator/CMA access. JointSpace has none. Measured: ntkmem is not a physmem map. |
| `ntkhdmi` | V4L2 capture/EDID/SCDC/infoframe/HPD and factory patterns. JointSpace only switches input. |
| `ntkiic0`/`/dev/i2c-*` | Raw I2C to panel/PMIC/tuner. JointSpace has none. High risk. |

## Next measurements (to convert UNKNOWN)

1. `ndp_led.ko`: disassemble `KER_LEDTop_IOCtl`; record the `cmp w1,#imm`
   switch and any `_IOC`-encoded constants. Do not run until measured.
2. `ndp_hdmi.ko`: write a V4L2 query harness (`VIDIOC_QUERYCAP`,
   `ENUMINPUT`, `G_INPUT`, `G_FMT`).
3. `ntgpio`/`ntkiic0`/`ndp_hwmem`: identify the owning code (likely
   `ndp_preinit.ko` or built-in) via strings from the kernel image or by
   symbol correlation; otherwise measure by controlled I/O only.
4. `ntktcon`: confirm whether `ndp_tcon.ko` is a 0-byte stub; if so, the tcon
   ioctl ABI lives in the built-in kernel image and needs a kernel-image read.

## Evidence

- Modules pulled read-only to workstation; hashes above.
- On-device `sha256sum` of `ntkctl`/`gpio_enum` matched workstation builds.
- Disassembly evidence: REA/Ghidra dossier for `ndp_misc.ko` `KER_MEM_IOCtl`
  (`0x2e00`, 370 instructions) in this session.

## Safety

No ioctl with a command was issued on-device in this phase; only open/close,
standard read-only GPIO lineinfo, and CDP listing. No `/dev` writes, no
`insmod`, no partition access. `uinput` and any vendor ioctl remain unrun.
