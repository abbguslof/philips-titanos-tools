# 2026-11-22 A/B switch: slot 0 is not licensed

Status: **TESTED-NEGATIVE / RECOVERY.** The A/B switch to the update slot 0
fails the XBoot `lnikauth` check. The TV remains in the XBoot loop; the old
slot 1/boot1 is intact. The recovery is a p9 DBFG write and an eMMC boot-part
change.

Target: Philips `55PUS8000/12`, mainboard `TPD.NT72690.PC762 (T)`, firmware
`TPA256E_V056.002.236.191`, kernel `6.1.124-gd063554eebf5-ab6`.

Method: [Level 4 boot-chain map](46-level4-boot-chain-map-2026-11-22.md), the
p9/boot-part switch, and the XBoot serial log.

## What changed

The pre-failure boot ran slot 1/boot1: XBoot rev `2a4184c`, p20 rootfs, p9
`DBFG` at `0x10` = 2, eMMC `PARTITION_CONFIG` = `0x50`, `lnikauth pass`.

The vendor update wrote slot 0/boot0: XBoot rev `5539e53bf`, p19 rootfs. The
TV never booted it.

The A/B test set p9 `0x10` = 1 and the eMMC boot part to 1
(`PARTITION_CONFIG` `0x48`), then rebooted to select slot 0.

## Result

The XBoot booted boot_area 0 and printed:

```text
boot_area: 0
[Secure] RPMB: 1, mode: 0
boot counter = 1
OBR,PowerOnEvt:LONG_PRESS_TO_OBR(38), IsBCOverLimit:0, need_mirror:0, switched:0, dual_all_same:0, addon_stats =2
Not allow to toggle boot area, reboot and try to let idtv clear DB.
[DEBUG]uart mode:0, sign:UMFG
lnikauth fail !
boot counter = 5
BC over limit
```

The known-good log from slot 1:

```text
boot_area: 1
boot counter = 1
OBR,PowerOnEvt:RC ON(3), IsBCOverLimit:0, need_mirror:0, switched:1, dual_all_same:0, addon_stats =2
[DEBUG]uart mode:0, sign:UMFG
lnikauth pass !
```

## Findings

- The `bc` field in the XBoot log is the p9 DBFG at `0x10`. Slot 1 boots with
  `bc:2`; the failing selection has `bc:1`. The p9 word selects the boot pair.
- Slot 0 fails `lnikauth`; slot 1 passes. The license is tied to the pair. The
  vendor update wrote slot 0 but did not license it. The earlier notes called
  slot 0 active; the live boot was slot 1.
- The eMMC boot part selects boot0 or boot1. The boot part alone does not
  override the p9 DBFG; the boot chain re-syncs the boot part to the DBFG. The
  app-layer `nvtfw_emmc_sync_dbflag_boot_part` does the same at runtime.
- The OBR cannot toggle the boot area while the DB says slot 0 and the boot
  counter reaches the limit. The `idtv` app clears the DB; slot 0 cannot boot
  `idtv`.
- The eMMC data is intact. The p9 DBFG and the boot part are the only changes.
  Slot 1/boot1 remains the licensed pair.
- The eMMC is a BGA-153 under the front heatsink. The pink pad on the back is a
  thermal pad, not the eMMC. The `EVA3`/`JPB` test pads, the `JTAG` (SoC), the
  HDMI labels, the `PWR UPGRADE` 12 V/GND connector, and the TCON are not the
  eMMC.
- The app-layer `nvtfw_enable_secure_boot` / `nvtfw_process_vtbl_cb` bypass
  changes only the userspace update path. It does not change the XBoot
  `lnikauth` check.

## Recovery

Write p9 `0x10` = `02 00 00 00`, or the live p9 image (sha256
`7e8fca3d…`). Set eMMC `EXT_CSD` `PARTITION_CONFIG` (index 179) = `0x50`
(boot part 2 / boot1). The XBoot rev `2a4184c` then boots boot1 with
`lnikauth pass`, Linux, root, and persistence.

The write needs an eMMC programmer (RT809H, Easy JTAG, Medusa) through a
BGA-153 socket or ISP adapter, or the 2026-11-14 full backup. A soldering iron
alone cannot program the eMMC. The board can go to a shop; the p9 image and the
two values are the whole brief.

The live p9 image, the full backup, and the board photos stay local. The board
photos contain serials and QR codes; they are not committed.

## Limits

- The recovery write is not done. The TV remains in the XBoot loop.
- The eMMC BGA and heatsink access are unproven; the board may go to a shop.
- The slot 0 license and the vendor update activation remain unresolved.
- No modified boot-area write.

## Evidence

[2026-11-22 A/B switch failure](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/deep/2026-11-22-ab-switch-failure.md).

## Related

- [Level 4 boot-chain map](46-level4-boot-chain-map-2026-11-22.md)
- [App-layer update gate](31-app-update-gate-2026-11-14.md)
- [Recovery engineering](26-recovery-engineering.md)
- [Recovery gate](../guides/recovery-gate.md)
