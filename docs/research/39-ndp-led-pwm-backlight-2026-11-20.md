# 2026-11-20 ndp_led PWM backlight (Level 3.5)

Status: **VERIFIED (hardware)** for the exported `KER_LED_PWM_HWFR_Get_Duty`
and `KER_LED_PWM_HWFR_Set_Duty` path. **OPEN** for the full ioctl and debug
menu, and for the 2D/3D channels.

Target: Philips `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`, kernel
`6.1.124-gd063554eebf5-ab6`.

Method: [Level 3.5 carrier](37-kernel-carrier-level-3-5.md), with the carrier's
`call` primitive.

## Why

Level 3.5 includes hardware control. The panel has no standard
`/sys/class/backlight` or `/sys/class/leds` interface on this build. The vendor
`ndp_led.ko` driver owns the PWM dimming path and exposes `/dev/ntkled`.

## Driver

| Item | Value |
| :--- | :--- |
| Module | `ndp_led.ko`, loaded |
| Device | `/dev/ntkled`, 502:0, mode `0666` |
| Sysfs | no `/sys/class/backlight`, no `/sys/class/leds` |
| DT | `TconLed` has only `interrupts`, `interrupt-affinity`, `name` |
| Ioctl | `KER_LEDTop_IOCtl` (not used in this test) |
| PWM | `KER_LED_PWM_HWFR_*`, `_PWMDIM_SetDuty_CH`, `genPWMDIMMode` |

The driver exports four GPL PWM functions. Two are enough for the backlight:

| Function | Signature | Behaviour |
| :--- | :--- | :--- |
| `KER_LED_PWM_HWFR_Get_Duty` | `int (u32 channel, u32 *duty, u32 *offset)` | channel < 13; writes duty and offset; returns 0 or -1 |
| `KER_LED_PWM_HWFR_Set_Duty` | `int (u32 channel, u32 duty, u32 offset)` | channel < 13; duty 0 rejected; the driver scales duty by 100; returns 0 or -1 |

`KER_LED_PWM_HWFR_Set_CH_EN(channel)` and `KER_LED_PWM_HWFR_Set` are not needed
for a duty change.

## Live test

The carrier scratch buffer held the two output words. Channel 0 was the only
nonzero channel.

| Step | Result |
| :--- | :--- |
| `Get_Duty(0, duty, offset)` | `0`, duty `20000`, offset `105` |
| `Set_Duty(0, 20000, 105)` | `0`; `Get_Duty` returned `20000`/`105` |
| `Set_Duty(0, 10000, 105)` | `0`; `Get_Duty` returned `10000`/`105`; the panel dimmed |
| hold 4 s, then `Set_Duty(0, 20000, 105)` | `0`; `Get_Duty` returned `20000`/`105` |
| reboot | `Get_Duty(0)` returned `20000`/`105` |

The duty change is visible on the panel for the 4 s hold and the restore returns
the original value. A reboot re-initialises the driver and returns the default
duty.

## Limits

- Channel 0 is the active hardware free-run channel. Channels 1 through 4 read
  zero on this boot.
- The duty units are the driver's internal units. `20000` is the current value
  and `10000` dims it. Do not assume a standard percent scale.
- The 2D/3D modes, the per-channel offset, the ioctl command set, and the debug
  menu are not mapped yet.
- The change is non-persistent. A reboot restores the driver default.
- No boot-chain, boot-area, or eMMC writes.

## Next

- Map the 2D/3D channels and the offset semantics.
- Reverse `KER_LEDTop_IOCtl` and the debug menu for the full surface.
- Move to the HDMI, Ambilight, and tuner ioctls.

## Evidence

[2026-11-20 ndp_led backlight](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-20-ndp-led-backlight.md).
