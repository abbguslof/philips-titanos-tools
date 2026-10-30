# Service Alignment Mode (SAM)

Status: **VERIFIED** on hardware for menu access and USB export/import.

## Enter SAM

1. Tune to an active input or channel.
2. Press **`123`** to show the numeric layer.
3. Enter **`0 6 2 5 9 6`**.
4. Press **`123`** again.
5. Press **`Info`**.

Customer Service Mode (read-only diagnostics):

```text
123 -> 1 2 3 6 5 4 -> 123 -> Info
```

## USB export/import

`Upload to USB` and `Download from USB` each expand into three targets:

| Target | USB path | Internal target |
| :--- | :--- | :--- |
| Channel list | `PhilipsChannelMaps/ChannelMap_100/` | DVB tuner tables and `chanLst.bin` |
| NVM copy | `SAM/nvm_ubootdat.data` | Partition p9 |
| EDID copy | `SAM/nvm_edid.data` | Display EDID table |

The SAM stick is **FAT32 with the label `PHILIPS`**, MBR partition table. This
is the opposite of the autorun stick, which must have an **empty label**. See
[the two USB workflows](../../GLOSSARY.md#usb-workflows).

Writing an NVM file is verified: the TV checks the dual CRC32, writes p9, shows
"Done", and reboots cleanly. `canary_test=1` and `bootdelay=5` survived a
round-trip. Use the [SAM guide](../guides/sam-download-from-usb.md) and keep a
pristine backup.

## Dealer options and the production lock

`Dealer Options -> Server Environment` offers `[Prod]`, `[Acc]`, `[Dev]`,
`[Test]`. On this retail unit, selecting anything other than `Prod` immediately
snaps back. Flashing `mds_mode=1`, `server_env=dev`, `sw_debug=1`, and
`watch_dog_timeout=0` into p9 did **not** change the selection and did **not**
unlock JointSpace engineering routes. The lock is in userspace, not NVM.

## Option bytes

The SAM `System Info` option bytes match the NVM dump:

```ini
OP1=160 000 020 068 009 037 008 236
OP2=147 004 002 148 194 036 024 000
OP3=032 014 000 098 032 177 197 059
OP4=255 000 000 000 000 000 001 012
```

These govern panel timing, tuner configuration, Ambilight zones, and CI+.
Do not edit them without a verified backup.

## EDID

`nvm_edid.data` is 932 bytes with an outer CRC32 at offset `0x00` covering
`0x04..EOF`. `tools/edid_tool.py` verifies it. The factory sample in
`samples/nvm/nvm_edid.data` passes.

## Recovery

If a SAM write goes wrong, restore the pristine NVM/EDID from your own backup
before changing anything else. SAM remains accessible as long as the graphical
UI initialises. See [restore to stock](../guides/restore-to-stock.md).
