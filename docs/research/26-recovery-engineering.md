# Recovery engineering for the 8000 lab

Status: **PLAN**. No boot-area writes until a restore has been proven.

The deepest jailbreak (Level 4) is a boot-chain project. Build a recovery path
before changing the boot chain. This page defines the recovery gate.

## What recovery must cover

| Layer | Failure | Recovery |
| :--- | :--- | :--- |
| Userspace root hook | Bad hook or service | USB autoroot + cold boot |
| Kernel module payload | Panic or hang | Cold boot; USB root |
| Kernel/ATF/boot-area write | No boot | eMMC ISP/JTAG or a proven boot slot |
| eMMC corruption | No boot | External eMMC programmer / ISP |
| Secure-boot rejection | No boot | Stock image restore only |

A cold boot is not a recovery for a corrupted bootloader.

## Current boot geometry

From `docs/research/02` and the live unit:

- `mmcblk0boot0` and `mmcblk0boot1` are 4 MiB eMMC boot areas; both contain
  XBoot on the tested unit.
- Vendor `p1`/`p2` are normal user-area partitions with the `UMFG` marker at
  `0x1A0200` (`p1=0`, `p2=1` on the tested unit).
- `p9` is `misc`; `p11` is `nvm_dat`; `p13–p18` and `p21` have U-Boot legacy
  magic; `p19/p20/p32–p35` are NFSB images; `p36` is pstore.
- The XBoot log reports `boot_area: 1`, but the exact boot-ROM/EXT_CSD selection
  rules are not mapped.

## Recovery research order

1. **Read-only inventory of the boot geometry.**
   - `tools/bootchain_dump.py` on the 8000.
   - `sha256sum` and size checks for every item; keep raw output under `dist/`.
   - Do not write any partition.
2. **eMMC boot-area switch research.**
   - Read `EXT_CSD` fields through a controlled read-only ioctl or a small
     helper; identify `PARTITION_CONFIG`, boot-bus width, boot-partition
     enables, and write-protect bits.
   - Determine which boot area the SoC selects and whether both are valid.
   - Determine whether `force_ro` can be cleared and later restored.
3. **A redundant boot slot.**
   - If the hardware can boot either boot area, preserve one stock area and use
     the other only after a tested restore.
   - If it cannot, the eMMC ISP path becomes mandatory.
4. **External eMMC recovery.**
   - Identify eMMC test points/package; determine whether an ISP/JTAG programmer
     can read and write the full device.
   - Capture a full image and verify a restore before any boot write.
5. **UART RX.**
   - Revisit the `SERV.U` RX path and the three UART MMIO windows.
   - Determine whether `uart_mode:0` is an ADC strap, a boot-partition field, or
     a hardware mux; do not assume the NVM variable is the source.
6. **Vendor update path.**
   - Determine whether SAM/USB update accepts raw `xboot`, ATF, kernel, or FDT
     components without an NFSB signature.
   - Map `UMFG`, `lnikauth`, `NVHC`, and any rollback check before testing.

## Full eMMC backup (do this first)

From the live root shell, with a USB filesystem large enough for the 7.3 GiB
user area plus the two 4 MiB boot areas:

```sh
mount -t ext4 /dev/sda1 /media/sda1
sh /media/sda1/emmc_backup.sh /media/sda1
```

`payloads/emmc_backup.sh` reads `/dev/mmcblk0`, `mmcblk0boot0` and
`mmcblk0boot1`, writes the images to the target, and writes a `SHA256SUMS`
file. It refuses an internal target, a non-USB target, a FAT32 target (4 GiB
limit), and insufficient free space. It does not write the eMMC.

If the TV cannot mount the target filesystem, for example an exFAT media drive,
pull the same images over SSH to a workstation filesystem. The 2026-11-14
backup used that path; see the
[recovery gate guide](../guides/recovery-gate.md).

Keep the USB copy and a second independent copy off the TV. This backup is the
recovery gate for the update-environment and boot-chain work.

## The restore test

Before a boot-chain write, prove the restore on the same unit:

1. Read the full boot area and the selected metadata partitions.
2. Compute hashes and keep two independent copies.
3. Write the same bytes back to the same area.
4. Cold boot and verify the stock boot log and root shell.
5. Only then consider a modified payload.

Do not use a modified image for the first restore test.

## Stop conditions

- No full backup.
- No verified restore.
- No way to select or recover the boot area.
- Any uncertainty about the partition's role.
- Secure-boot rejection with no stock-image restore.

## What this unlocks

A proven restore turns the 8000 into a lab where a bad boot stage is
recoverable. That is the gate to Phase D (dual-boot) and Level 4.

It does not unlock DRM or secure-world keys. Those are separate trust
boundaries and remain out of scope.
