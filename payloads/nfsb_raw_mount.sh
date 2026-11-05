#!/bin/sh
# Read-only mount of the SquashFS inside an NFSB partition.
#
# Usage: nfsb_raw_mount.sh <partition> <mountpoint> [offset-bytes]
#
# The NFSB header is 0x1000 bytes. The tool copies the partition from that
# offset, attaches the copy read-only, and mounts it with the stock squashfs
# driver. It writes only to /tmp. Run it on the TV as root.

set -eu

usage() {
    echo "usage: $0 <partition> <mountpoint> [offset-bytes]" >&2
    echo "example: $0 /dev/nvt-part-name/fs1 /tmp/stock-rootfs" >&2
    exit 2
}

[ "$#" -ge 2 ] || usage

part=$1
mnt=$2
offset=${3:-4096}

[ "$(id -u)" = "0" ] || {
    echo "error: run as root" >&2
    exit 1
}
[ -b "$part" ] || {
    echo "error: not a block device: $part" >&2
    exit 1
}
[ "$offset" -ge 4096 ] || {
    echo "error: offset must be at least 4096" >&2
    exit 1
}

blocks=$((offset / 4096))
if [ "$((blocks * 4096))" -ne "$offset" ]; then
    echo "error: offset must be a multiple of 4096" >&2
    exit 1
fi

tmp=/tmp/nfsb-raw.$$
loop=
success=0
cleanup() {
    if [ "$success" -eq 1 ]; then
        return 0
    fi
    if [ -n "$loop" ] && mount | grep -q " $mnt "; then
        umount "$mnt" 2>/dev/null || true
    fi
    if [ -n "$loop" ]; then
        losetup -d "$loop" 2>/dev/null || true
    fi
    rm -f "$tmp"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$mnt"
echo "copying $part from offset $offset to $tmp"
if ! dd if="$part" of="$tmp" bs=4096 skip="$blocks" 2>/dev/null; then
    echo "error: copy failed" >&2
    exit 1
fi

loop=$(losetup -f)
losetup -r "$loop" "$tmp"
mount -t squashfs -o ro "$loop" "$mnt"

success=1
echo "mounted $part at $mnt via $loop (read-only)"
echo "cleanup: umount $mnt; losetup -d $loop; rm -f $tmp"
ls -l "$mnt" | head
