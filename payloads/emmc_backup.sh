#!/bin/sh
# Read-only full eMMC backup to a mounted external USB filesystem.
#
# Run as root on the TV from the root shell:
#   mount -t ext4 /dev/sda1 /media/sda1
#   sh /media/sda1/emmc_backup.sh /media/sda1
#
# Writes only to the target directory. Reads /dev/mmcblk0 and the two eMMC boot
# areas. The target must be a USB (/dev/sd*) filesystem with room for the user
# area plus the boot areas. A FAT32 target is refused because the user-area image
# is larger than 4 GiB; use ext4 or another large-file filesystem.
#
# This is the recovery-gate backup. Keep a second copy off the TV and verify the
# SHA-256 file before any boot-area experiment.

set -eu

DST=${1:-/media/sda1}
[ "$(id -u)" = "0" ] || { echo "ERROR: must run as root"; exit 1; }
[ -d "$DST" ] || { echo "ERROR: target is not a directory: $DST"; exit 1; }

DEV=$(df -P "$DST" 2>/dev/null | tail -n 1 | awk '{print $1}')
case "$DEV" in
    /dev/sd*) ;;
    *) echo "ERROR: target $DST is on '$DEV', not a USB /dev/sd* device"; exit 1 ;;
esac

FS=$(mount | grep " on $DST " | sed -n 's/.* type \([^ ]*\).*/\1/p' | head -n 1)
case "$FS" in
    vfat|msdos) echo "ERROR: $FS cannot hold a >4 GiB image; use ext4 or exfat"; exit 1 ;;
esac

AVAIL_KB=$(df -Pk "$DST" | tail -n 1 | awk '{print $4}')
NEED_KB=$((7634944 + 16384))
if [ "${AVAIL_KB:-0}" -lt "$NEED_KB" ]; then
    echo "ERROR: need at least ${NEED_KB} KiB free on $DST, have ${AVAIL_KB:-0} KiB"
    exit 1
fi

echo "target: $DST ($FS)"
echo "user area: /dev/mmcblk0 (7634944 KiB)"
echo "boot areas: /dev/mmcblk0boot0, /dev/mmcblk0boot1"
echo "this is read-only on the eMMC; do not interrupt it"

dd if=/dev/mmcblk0 of="$DST/emmc-user.img" bs=1048576
dd if=/dev/mmcblk0boot0 of="$DST/mmcblk0boot0.img" bs=4096
dd if=/dev/mmcblk0boot1 of="$DST/mmcblk0boot1.img" bs=4096
sync

cd "$DST"
sha256sum emmc-user.img mmcblk0boot0.img mmcblk0boot1.img > SHA256SUMS
sync

echo "backup complete:"
ls -lh emmc-user.img mmcblk0boot0.img mmcblk0boot1.img SHA256SUMS
echo "verify before any experiment:"
echo "  sha256sum -c SHA256SUMS"
