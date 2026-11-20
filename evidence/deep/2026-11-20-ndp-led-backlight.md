# 2026-11-20 ndp_led PWM backlight

Status: **VERIFIED (hardware)** for the exported `KER_LED_PWM_HWFR_Get_Duty`
and `KER_LED_PWM_HWFR_Set_Duty` path. **OPEN** for the full ioctl/debug menu and
the 2D/3D channels.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [research/39](../../docs/research/39-ndp-led-pwm-backlight-2026-11-20.md),
[research/37](../../docs/research/37-kernel-carrier-level-3-5.md).

Kernel addresses are omitted. The module offsets below are file-relative.

## Module

| Item | Value |
| :--- | :--- |
| `ndp_led.ko` | `ed7cb3e749a60c8ae25326f40b988f8f3dd28576908538ff922b9c124dc1dc2f` |
| Device | `/dev/ntkled`, 502:0, mode `0666` |
| Sysfs | no `/sys/class/backlight`, no `/sys/class/leds` |
| DT `TconLed` | `interrupts`, `interrupt-affinity`, `name` only |
| Ioctl | `KER_LEDTop_IOCtl` (not used) |
| PWM | `KER_LED_PWM_HWFR_*`, `_PWMDIM_SetDuty_CH`, `genPWMDIMMode` |

## Exported functions

| Function | Signature | Notes |
| :--- | :--- | :--- |
| `KER_LED_PWM_HWFR_Get_Duty` | `int (u32 channel, u32 *duty, u32 *offset)` | channel < 13; returns 0 or -1 |
| `KER_LED_PWM_HWFR_Set_Duty` | `int (u32 channel, u32 duty, u32 offset)` | channel < 13; duty 0 rejected; internal duty is `duty * 100` |

`KER_LED_PWM_HWFR_Set_CH_EN` and `KER_LED_PWM_HWFR_Set` were not used.

## Live test

The carrier scratch buffer held the two output words. Channel 0 was the only
nonzero channel.

| Step | Result |
| :--- | :--- |
| `Get_Duty(0)` | `0`; duty `20000`, offset `105` |
| `Set_Duty(0, 20000, 105)` | `0`; `Get_Duty` returned `20000`/`105` |
| `Set_Duty(0, 10000, 105)` | `0`; `Get_Duty` returned `10000`/`105`; panel dimmed |
| hold 4 s, restore `20000`/`105` | `0`; `Get_Duty` returned `20000`/`105` |
| reboot | `Get_Duty(0)` returned `20000`/`105` |

The panel output followed the duty change during the 4 s hold. The restore
returned the original value. The change is runtime-only; the reboot re-initialised
the driver.

## Rollback

- Restore the original duty with `Set_Duty(0, 20000, 105)`.
- Unload the carrier and restore the seloff module.
- A reboot re-initialises the LED driver and returns the default duty.

## Limits

- Channel 0 was the active hardware free-run channel. Channels 1 through 4 read
  zero.
- The duty units are the driver's internal units, not a standard percent scale.
- The 2D/3D modes, the offset semantics, the ioctl command set, and the debug
  menu are not mapped.
- No boot-chain, boot-area, or eMMC writes.
