# Flash layout and partitions

Status: **VERIFIED** from the live root shell (`/proc/partitions`, `/proc/mounts`)
and from partition dumps.

## Two different things called `boot0`

This is the most common source of confusion in the notes. They are not the same
partition:

| Name | Device on the TV | What it is |
| :--- | :--- | :--- |
| **eMMC boot partition** | `/dev/mmcblk0boot0`, `/dev/mmcblk0boot1` | Two 4 MiB eMMC boot areas. Both contain the XBoot image on this unit. |
| **Vendor `boot0` partition** | `/dev/nvt-part-name/boot0` → `mmcblk0p1` | A normal user-area partition. `mmcblk0p2` (vendor `boot1`) also carries the `UMFG` marker. |

The vendor script `board/run.sh` reads `UMFG` from the **vendor boot0 partition**
at byte `1704448` (`0x1A0200`). The eMMC boot partitions are not the source of
that read. See [file formats](../reference/file-formats.md#umfg-and-debug_func_level).

## User-area partitions

`mmcblk0` reports **40 partitions** and a capacity of `7634944 KiB`. The
following are verified from the root shell:

| Partition | Mount / role | Notes |
| :--- | :--- | :--- |
| p1 | vendor `boot0` | `UMFG` at `0x1A0200`; slice value `0` on the tested unit. |
| p2 | vendor `boot1` | `UMFG` at `0x1A0200`; slice value `1` on the tested unit. |
| p3, p4 | DDR config (`DDRC` magic) | Not mounted as a filesystem in userspace. |
| p7, p8 | `PIDX` magic | Not identified further. |
| p9 | U-Boot-style NVM environment | Exported as `SAM/nvm_ubootdat.data`; see [NVM format](04-uboot-nvm-format.md). |
| p13–p18, p21 | U-Boot legacy magic (`27 05 19 56`) | Raw images; not mounted. |
| p19, p20, p32–p35 | `NFSB` secure filesystem images | p20 is the rootfs (`/`), SquashFS read-only. |
| p31 | `apdat` → `/mtd_rwarea` | **rw ext4.** This is the persistence partition. |
| p36 | pstore | `nvt_pstore_mmc.blkdev=/dev/mmcblk0p36`. |

The kernel command line confirms the important ones:

```text
root=/dev/mmcblk0p20 ro
nvt_pstore_mmc.blkdev=/dev/mmcblk0p36
```

Do not use the old p17/p33 numbers from early notes; they were wrong.

## Mounted volumes on the live TV

From `/proc/mounts` in the root shell:

| Device | Mount | Access |
| :--- | :--- | :--- |
| `/dev/root` | `/` | squashfs, ro |
| `/dev/mapper/mtd_apexe` | `/mtd_apexe` | squashfs, ro (NFSB) |
| `/dev/mapper/apexe_ext` | `/apexe_ext` | squashfs, ro (NFSB) |
| `/dev/nvt-part-name/channel_fac` | `/chanfac` | ext4, ro |
| `/dev/nvt-part-name/misc_tmp` | `/misctmp` | ext4, rw |
| `/dev/nvt-part-name/devcfg` | `/tkconfig` | ext4, ro |
| `/dev/nvt-part-name/devcfg_rw` | `/devcfg_rw` | ext4, rw |
| `/dev/nvt-part-name/frc_fw` | `/frcfw` | ext4, ro |
| `/dev/nvt-part-name/demo` | `/demo` | ext4, rw |
| `/dev/nvt-part-name/aq` | `/aqtbl` | ext4, ro |
| `/dev/nvt-part-name/pq` | `/pqtbl` | ext4, ro |
| `/dev/nvt-part-name/nvm_file` | `/nvm_file` | ext4, rw |
| `/dev/nvt-part-name/sw_dl` | `/swdl` | ext4, rw |
| `/dev/nvt-part-name/apdat` | `/mtd_rwarea` | ext4, **rw** |
| `/dev/nvt-part-name/tmpdat` | `/mtd_tmpdat` | ext4, rw |

`/mtd_apdat` is a symlink to `/mtd_rwarea/apdat`. The vendor `run.sh` sources
`/mtd_apdat/customer_env.sh`; that is the persistence hook. See
[persistence](06-persistence-customer-env.md).

## SELinux

`/sys/fs/selinux/enforce` reads `1` (enforcing). Writing `0` fails with
`Invalid argument` on this build. The root path works under the `initrc_t`
domain; the USB payload and persistent hook do not disable SELinux. Files under
`/mtd_rwarea/apdat` are labelled `idtv_data_t`; the persistence installer runs
`restorecon` on the files it creates.

## Evidence

- `evidence/usb-autoroot/v3-telnetd-listen/diag3.txt` — root, SELinux, serial, IP.
- `evidence/usb-autoroot/v7-autoroot-success/autoroot.log` — exact kernel
  command line and mount list.
- `evidence/usb-autoroot/v5-umfg-partitions/` — 32-byte `UMFG` slices from p1
  and p2. The full 4 MiB dumps are not published.
