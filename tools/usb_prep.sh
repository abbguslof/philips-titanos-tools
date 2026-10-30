#!/usr/bin/env bash
#
# Prepare USB Thumb Drive for Philips Titan OS Service Alignment Mode (SAM)
# Strict requirements:
#   - MBR (DOS) partition table (GPT often fails in Novatek U-Boot)
#   - Single FAT32 partition
#   - Volume label: PHILIPS
#
# Usage:
#   sudo ./usb_prep.sh /dev/sdX
#

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: sudo $0 <device>  (e.g. /dev/sdb)" >&2
    exit 1
fi

DEVICE="$1"

if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (sudo)." >&2
    exit 1
fi

if [[ ! -b "$DEVICE" ]]; then
    echo "Error: Device '${DEVICE}' does not exist or is not a block device." >&2
    exit 1
fi

# Sanity check: prevent wiping system disk
ROOT_DEV=$(findmnt -n -o SOURCE / | sed 's/[0-9]*$//; s/p[0-9]*$//')
if [[ "$DEVICE" == "$ROOT_DEV"* ]]; then
    echo "SAFETY ABORT: Refusing to format root device '${DEVICE}'!" >&2
    exit 1
fi

echo "=========================================================="
echo "WARNING: All data on '${DEVICE}' will be permanently ERASED!"
echo "Target: MBR partition table with 1x FAT32 partition (PHILIPS)"
echo "=========================================================="
read -r -p "Type 'YES' to proceed with formatting: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
    echo "Aborted."
    exit 0
fi

echo "1. Unmounting existing partitions..."
umount "${DEVICE}"* 2>/dev/null || true

echo "2. Wiping existing partition tables and signatures..."
wipefs -a "${DEVICE}"

echo "3. Creating MBR partition table using entire disk..."
sfdisk "${DEVICE}" << EOF
label: dos
,,c,*
EOF

# Give kernel and udev time to re-read partition table
sync
partprobe "${DEVICE}" 2>/dev/null || blockdev --rereadpt "${DEVICE}" 2>/dev/null || true
udevadm settle 2>/dev/null || sleep 2

# Determine correct partition node name
if [[ "${DEVICE}" =~ [0-9]$ ]]; then
    PART="${DEVICE}p1"
else
    PART="${DEVICE}1"
fi

# Wait for block device to appear
for i in {1..5}; do
    if [[ -b "${PART}" ]]; then
        break
    fi
    sleep 1
done

if [[ ! -b "${PART}" ]]; then
    echo "Error: Partition '${PART}' was not created or detected." >&2
    exit 1
fi

echo "4. Formatting ${PART} as FAT32..."
mkfs.fat -F 32 -n "PHILIPS" "${PART}"
sync

echo "✓ Formatting complete! Plug into USB Port 1 on the Philips TV."
