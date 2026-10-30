# Restore to stock

Use the smallest tier that solves the problem. The documented root paths do not
write to flash, so most experiments need only a cold boot.

## Tier 1: Remove the USB autorun

1. Pull the USB stick.
2. Unplug AC for 10 seconds.
3. Plug in.

The shell, `/tmp/busybox`, and the `iptables` rule are gone. The TV boots
normally. Nothing was written to flash.

## Tier 2: Remove the persistence hook

From any root shell (USB or persistent):

```sh
sed -i '/root_boot.sh/d' /mtd_rwarea/apdat/customer_env.sh
rm -f /mtd_rwarea/apdat/root_boot.sh /mtd_rwarea/apdat/busybox \
      /mtd_rwarea/apdat/root_boot.log /mtd_rwarea/apdat/root_boot.ready \
      /mtd_rwarea/apdat/root_boot.ready.failed
```

If you want to be extra sure, inspect the file first:

```sh
cat /mtd_rwarea/apdat/customer_env.sh
```

If `customer_env.sh` was created only by this project and contains nothing else,
you can remove it entirely:

```sh
rm -f /mtd_rwarea/apdat/customer_env.sh
```

Then cold boot. The TV should no longer listen on `:2323`.

## Tier 3: SAM NVM/EDID restore

Only needed if you wrote NVM/EDID data and want the factory values back.

1. Copy your pristine `SAM/nvm_ubootdat.data` and `SAM/nvm_edid.data` to an
   MBR/FAT32 stick labelled `PHILIPS`.
2. Enter SAM: `123` -> `062596` -> `123` -> `Info`.
3. `Download from USB` -> `NVM copy` (or `EDID copy`).
4. Wait for "Done", then cold boot.
5. Verify by exporting again and running:

```bash
python3 tools/uboot_nvm_tool.py verify SAM/nvm_ubootdat.data
python3 tools/edid_tool.py verify SAM/nvm_edid.data
```

The factory sample in `samples/nvm/` is a sanity check, not a substitute for
your own backup.

## Tier 4: Factory reset / virgin mode

Inside SAM, `Dealer Options -> Set Virgin Mode` forces the initial installation
wizard on the next boot and erases user data. It does not restore a modified
rootfs or bootloader.

## What not to do

- Do not flash a modified rootfs or an `init=` parameter. There is no serial
  recovery on this build; a kernel panic before the UI means SAM is unavailable.
- Do not write to the eMMC boot partitions (`mmcblk0boot0`/`boot1`) or the
  vendor `boot0` (`mmcblk0p1`) without a proven recovery path.
- Do not use a firmware package for a different chassis or `Main SW ID`.
