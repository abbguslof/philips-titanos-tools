# Runtime NFSB bypass: raw SquashFS mount

Status: **VERIFIED on hardware**, 2026-11-05.

The NFSB verifier runs when the kernel mounts an image through the `nfsb`
filesystem. A direct `mount -t squashfs` of the inner filesystem does not call
that verifier. The inner SquashFS starts at offset `0x1000`. A copy of the
partition from that offset mounts read-only with no NFSB header, RSA check, or
dm-verity.

The boot-time NFSB mount and the signed boot chain do not change. This page
covers the runtime read-only mount. A modified NFSB image still cannot boot or
flash.

## Verified result

The active rootfs is `fs1` (`mmcblk0p20`). The read-only mount of the stock
rootfs:

```sh
dd if=/dev/nvt-part-name/fs1 of=/tmp/fs1.sqsh bs=4096 skip=1
losetup -r /dev/loop1 /tmp/fs1.sqsh
mkdir -p /tmp/sqsh
mount -t squashfs -o ro /dev/loop1 /tmp/sqsh
head -5 /tmp/sqsh/etc/init.d/S21idtv.sh
```

`mount` returns 0 and the shell reads the stock init script. The
`payloads/nfsb_raw_mount.sh` tool performs the same steps and cleans up the loop
device. It strips the first 4,096 bytes, attaches the copy read-only, and mounts
it read-only.

The application and UI images work the same way. `apexe_ext1` (`p35`) is about
550 MiB, so check `/tmp` free space before copying it. The rootfs (`fs0`/`fs1`)
is about 30 MiB.

## What the NFSB verifier does

A normal NFSB mount verifies the header and creates dm-verity targets:

```sh
mount -t nfsb -o ro /dev/nvt-part-name/fs0 /tmp/nfsbtest
```

```text
NFSB header found and verified.
dm: target linear of size 61432 on 253:10(253:10) is ready
device-mapper: verity: sha256 using implementation "sha256-ce"
dm: target verity of size 38080 on 253:11(253:11) is ready
```

The running kernel exports `nfsb_verify`, `nvt_dm_check_nfsb`,
`dm_check_nfsb`, and `nfsb` helper symbols. The NFSB header carries the SHA-256
root and the RSA signature. The kernel builds the dm-verity target from that
header.

A modified copy of the same image still mounts through `nfsb`, because the
header remains valid. dm-verity catches the changed data when a read touches the
modified block:

```text
device-mapper: verity: 253:14: data block 255 is corrupted
SQUASHFS error: Failed to read block ...
```

A forced full read returns `Input/output error` on the modified file. The
verifier is active for the `nfsb` mount. The raw `squashfs` mount of a copy does
not use it.

## Mount a custom SquashFS

A host-built SquashFS can be copied to the TV and mounted the same way. The
stock kernel supports SquashFS with LZO, so `mksquashfs -comp lzo` matches the
stock images. Build with the labels needed by the TV, or bind the stock labeled
executables over the custom tree. The host filesystem usually lacks the stock
`security.selinux` xattrs, and this kernel rejects `mount -o context=...` on
SquashFS. A downstream custom layer has to handle that boundary. The public
repo stops at the read-only mount.

## What this does not do

- It does not make a modified NFSB image bootable or flashable.
- It does not re-sign the NFSB header or change the RSA root.
- It does not bypass XBoot, ATF, the encrypted kernel, the FDT, or the `NVHC`
  slot checks.
- It does not survive a reboot unless a persistent hook mounts the image again.
- It does not write the partition. The mount is read-only.

Do not flash Track B or the eMMC boot areas. The boot chain has no proven
unbrick path.

## Prerequisites

- Root on the TV over TCP `:2323` from the USB autoroot path.
- Physical access to the TV.
- Enough free space in `/tmp` for the partition copy.
- An owned TV. This is not a remote exploit.

## Evidence

- [Runtime NFSB evidence](../../evidence/runtime-nfsb/README.md)
- [Firmware container](03-firmware-container-timg-pimg-nfsb.md)
- [Verified findings and dead ends](12-verified-findings-and-dead-ends.md)

## Open questions

- Whether the boot-time NFSB verifier can be bypassed without the vendor RSA
  key. The `NVHC` and the encrypted boot images add more checks.
- Whether a future firmware release changes the NFSB header layout or the
  dm-verity parameters.
- Whether a custom image can carry the stock SELinux labels through the build.
