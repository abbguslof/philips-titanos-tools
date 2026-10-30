# Partition map

Canonical numbers for the verified unit. `mmcblk0` is 7,634,944 KiB with 40
user-area partitions. The two eMMC boot areas are separate devices.

| Device | Name / role | Access | Notes |
| :--- | :--- | :--- | :--- |
| `mmcblk0boot0` | eMMC boot area | block device | 4 MiB; XBoot image. |
| `mmcblk0boot1` | eMMC boot area | block device | 4 MiB; XBoot image. |
| `mmcblk0p1` | vendor `boot0` | raw | `UMFG` at `0x1A0200`, value `0` on the tested unit. |
| `mmcblk0p2` | vendor `boot1` | raw | `UMFG` at `0x1A0200`, value `1` on the tested unit. |
| `mmcblk0p3` | DDR config | raw | `DDRC` magic. |
| `mmcblk0p4` | DDR config | raw | `DDRC` magic. |
| `mmcblk0p7` | indexed data | raw | `PIDX` magic. |
| `mmcblk0p8` | indexed data | raw | `PIDX` magic. |
| `mmcblk0p9` | NVM environment | raw / SAM | `nvm_ubootdat.data`; `DBFG` magic. |
| `mmcblk0p13`–`p18` | U-Boot legacy images | raw | `27 05 19 56` magic. |
| `mmcblk0p19` | `NFSB` secure fs | mapped | Not rootfs. |
| `mmcblk0p20` | rootfs | squashfs ro | `/`; `root=/dev/mmcblk0p20`. |
| `mmcblk0p21` | U-Boot legacy image | raw | `27 05 19 56` magic. |
| `mmcblk0p31` | `apdat` | ext4 rw | `/mtd_rwarea`; `/mtd_apdat` symlink. |
| `mmcblk0p32`–`p35` | `NFSB` secure fs | mapped | Application/UI images. |
| `mmcblk0p36` | pstore | raw | `nvt_pstore_mmc.blkdev`. |

## Mounted named volumes

| Mount | Source | Access |
| :--- | :--- | :--- |
| `/` | `mmcblk0p20` | ro |
| `/mtd_apexe` | mapped `mtd_apexe` | ro |
| `/apexe_ext` | mapped `apexe_ext` | ro |
| `/chanfac` | `channel_fac` | ro |
| `/misctmp` | `misc_tmp` | rw |
| `/tkconfig` | `devcfg` | ro |
| `/devcfg_rw` | `devcfg_rw` | rw |
| `/frcfw` | `frc_fw` | ro |
| `/demo` | `demo` | rw |
| `/aqtbl` | `aq` | ro |
| `/pqtbl` | `pq` | ro |
| `/nvm_file` | `nvm_file` | rw |
| `/swdl` | `sw_dl` | rw |
| `/mtd_rwarea` | `apdat` | rw |
| `/mtd_tmpdat` | `tmpdat` | rw |

See [flash layout](../research/02-flash-layout-and-partitions.md) for the
evidence and the two-`boot0` warning.
