# SAM: Download from USB

Status: **VERIFIED** on hardware for NVM and EDID. This guide is for the
technician service menu, not the autorun stick.

## Prepare the SAM stick

- MBR partition table, one FAT32 partition.
- Volume label **`PHILIPS`** (this is the opposite of the autorun stick).
- Contents:

```text
SAM/nvm_ubootdat.data
SAM/nvm_edid.data
PhilipsChannelMaps/ChannelMap_100/...
```

`tools/usb_prep.sh` formats a labelled stick for this workflow. `stage_usb.py`
stages a stock/canary/diagnostic NVM profile and verifies the dual CRC32.

```bash
sudo ./tools/usb_prep.sh /dev/sdX
./tools/stage_usb.py /run/media/$USER/PHILIPS --mode canary
```

## Enter SAM

1. Tune to an active input or channel.
2. Press `123`, enter `062596`, press `123`, press `Info`.
3. The SAM HUD appears.

## Write NVM

1. Insert the stick.
2. `Download from USB` -> `NVM copy`.
3. The TV reads `SAM/nvm_ubootdat.data`, verifies both CRC32 layers, writes p9,
   and reports "Done".
4. Cold boot.

Verify by exporting again:

```bash
./tools/uboot_nvm_tool.py verify /run/media/$USER/PHILIPS/SAM/nvm_ubootdat.data
./tools/uboot_nvm_tool.py get    /run/media/$USER/PHILIPS/SAM/nvm_ubootdat.data canary_test
```

## Write EDID

`Download from USB` -> `EDID copy`. Use only your own factory EDID or a verified
replacement.

## Channel list

`Download from USB` -> `Channel list` imports `PhilipsChannelMaps/ChannelMap_100/`.
`chanLst.bin` carries CRC-16/MODBUS checksums; use
`tools/channel_map_tool.py recalculate` after editing the XML files.

## Safety

- Keep a pristine backup of NVM and EDID.
- Do not inject `init=`/`bootargs=`; there is no serial recovery.
- `mds_mode=1` does not unlock the userspace `tvtype: consumer` gate; do not
  expect it to change SAM's `Server Environment` behavior.
- `bootdelay=5` is accepted but inert because there is no interactive U-Boot.

See [restore to stock](restore-to-stock.md) if a write goes wrong.
