# Recovery gate: back up the eMMC before boot-chain work

Status: **VERIFIED backup**, **same-byte restore tested on both boot areas**.
A deliberately corrupted boot area is still untested. This is the gate from the
[deep jailbreak roadmap](../research/25-deep-jailbreak-roadmap.md) and
[recovery engineering](../research/26-recovery-engineering.md).

Do not write a boot area, a boot image, or the update environment until you
have a full backup and a tested restore. A cold boot is not a recovery for a
corrupted bootloader.

## What to back up

- `/dev/mmcblk0` (7,634,944 KiB user area).
- `/dev/mmcblk0boot0` and `/dev/mmcblk0boot1` (4 MiB each).
- The boot metadata: `p1`, `p2`, `p9`, `p11`, `p36`, and the NFSB headers.
- Keep the backup off the TV in two independent copies.

## Path A: ext4 USB on the TV

Use this when the TV can mount the target filesystem. The tested TV supports
ext4, ext2, ext3, vfat, msdos, iso9660, ntfs, and fuse. It has no exFAT driver.

```sh
# workstation: format a spare USB as ext4
sudo -n wipefs -a /dev/sdX
sudo -n sfdisk /dev/sdX <<'EOF'
label: dos
,,83
EOF
sudo -n mkfs.ext4 -L TITANBK /dev/sdX1
```

```sh
# TV, as root
mount -t ext4 /dev/sda1 /media/sda1
df -Pk /media/sda1          # need at least 7,651,328 KiB free
/tmp/busybox wget -O /tmp/emmc_backup.sh http://<WORKSTATION_IP>:8000/payloads/emmc_backup.sh
sh /tmp/emmc_backup.sh /media/sda1
cd /media/sda1 && sha256sum -c SHA256SUMS
```

`payloads/emmc_backup.sh` refuses a target that is not a `/dev/sd*` device, a
`vfat`/`msdos` target, or a target with less than 7,651,328 KiB free.

## Path B: network pull to the workstation

Use this when the drive is not mountable on the TV, for example an exFAT media
drive. The pull is read-only on the TV and supports files over 4 GiB on the
workstation side.

```sh
# workstation
mkdir -p /path/to/backup
ssh -p 2222 root@<TV_IP> 'dd if=/dev/mmcblk0 bs=1048576' > /path/to/backup/emmc-user.img
ssh -p 2222 root@<TV_IP> 'dd if=/dev/mmcblk0boot0 bs=4096' > /path/to/backup/mmcblk0boot0.img
ssh -p 2222 root@<TV_IP> 'dd if=/dev/mmcblk0boot1 bs=4096' > /path/to/backup/mmcblk0boot1.img
cd /path/to/backup && sha256sum emmc-user.img mmcblk0boot0.img mmcblk0boot1.img > SHA256SUMS
sha256sum -c SHA256SUMS
```

The 2026-11-14 backup used this path because the available media drive is
exFAT and the TV has no exFAT driver. See
[the backup evidence](../../evidence/deep/2026-11-14-emmc-backup.md).

For the boot and metadata partitions, use the repo tool:

```sh
python3 tools/bootchain_dump.py --host <TV_IP> --full-boot --out dist/bootchain/<date>
python3 tools/bootchain_inspect.py --dir dist/bootchain/<date>
```

## Verify

- `emmc-user.img` is 7,818,182,656 bytes.
- Each boot area image is 4,194,304 bytes.
- `sha256sum -c SHA256SUMS` passes on the TV and on a second machine.
- The bootchain manifest records a `sha256` and `complete: true` for each item.
- Keep a second copy on a different device.

## Restore test

Do this before any modified payload. It is a write.

1. Read the boot area and the selected metadata partitions.
2. Keep two verified copies.
3. Write the same bytes back to the same area.
4. Cold boot and verify the stock boot log and the root shell.

2026-11-14 result: the stock bytes were written back to `mmcblk0boot0` and
`mmcblk0boot1`, read back, and cold-booted after each write. Both boots
returned `uid=0` with a fresh uptime and a new `root_boot.ready`; both areas
stayed `force_ro=1` and hash `eee415…`. The same-byte restore is verified.

Do not use a modified image for the first restore test. Recovery from a
deliberately corrupted boot area is still untested; it needs the eMMC
boot-area selection or ISP/JTAG path.

## Stop conditions

- No full backup.
- No verified restore of a deliberately corrupted boot area.
- No way to select or recover the boot area.
- Any uncertainty about the partition's role.
- Field units: do not write.

The update-path analysis and the prepared dump-only test package are in
[research/30](../research/30-update-path-2026-11-14.md). The package is blocked
on this gate.
