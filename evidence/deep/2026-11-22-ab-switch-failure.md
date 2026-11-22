# 2026-11-22 A/B switch failure and recovery data

Status: **TESTED-NEGATIVE.** The A/B switch to slot 0 fails the XBoot
`lnikauth` check. The TV stays in the XBoot loop. The recovery values are
below.

Target: Philips `55PUS8000/12`, mainboard `TPD.NT72690.PC762 (T)`, firmware
`TPA256E_V056.002.236.191`, kernel `6.1.124-gd063554eebf5-ab6`.

## Pre-failure live state

- XBoot rev `2a4184c`, `boot_area 1`, `bc:2`, `RC ON(3)`, `switched:1`,
  `lnikauth pass`.
- p9 `7e8fca3d37187a48b061565d42f68df9039df595e7c7c3eaac087cfa0872fec9`;
  DBFG `0x10` = 2.
- eMMC `PARTITION_CONFIG` = `0x50` (boot part 2).
- Hashes: boot0 `1c74949e…`, boot1 `eee41501…`, p1 `e7698f8f…`,
  p2 `756355f8…`, p19 `49f81af3…`, p20 `e6aa3850…`.

## Test

- Write p9 `0x10` = 1.
- Set eMMC `PARTITION_CONFIG` from `0x50` to `0x48` (boot part 1).
- Reboot.

## Result

- `boot_area 0`, XBoot rev `5539e53bf`, `lnikauth fail`.
- `boot counter` 1 to 5; `BC over limit`.
- OBR `LONG_PRESS_TO_OBR(38)` and `OBR_SWITCH(224)`; `switched:0`;
  `Not allow to toggle boot area, reboot and try to let idtv clear DB.`
- Slot 0 did not boot. No serial or SSH.

## Recovery values

- p9 `0x10` = `02 00 00 00`, or the p9 image above.
- eMMC `EXT_CSD` `PARTITION_CONFIG` (index 179) = `0x50`.
- The XBoot rev `2a4184c` then boots boot1 with `lnikauth pass`.
- eMMC is a BGA-153 under the front heatsink. Use an RT809H, Easy JTAG, or
  Medusa with a BGA-153 socket or ISP adapter. Fallback: the 2026-11-14 full
  eMMC backup with boot part `0x50`.
- The p9 image and the full backup are local and gitignored. The board photos
  stay local.

## Limits

- No recovery write was made.
- The eMMC BGA and heatsink access are unproven.
- No modified boot-area write.
- Slot 0 license and vendor update activation remain unresolved.
