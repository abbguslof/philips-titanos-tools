# Boot image map: protected secure slots and the plain kerupm kernel

Status: **VERIFIED (read-only)** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-12. No boot-area or partition writes.

Phase B produced this map. The tools and raw dumps live under `dist/`
(gitignored); only hashes and summaries are published.

## Method

- `tools/deep_probe.py` collected the live inventory.
- `tools/bootchain_dump.py --full-boot` pulled the boot and metadata
  partitions to the workstation over SSH. The TV was only read.
- `tools/bootchain_inspect.py` parsed U-Boot legacy uImage headers, verified
  CRCs, measured payload entropy, and found embedded images and strings.

The raw partitions are not published: the NVM and boot slots may contain device
identity data.

## Boot images

| Partition | uImage name / type | Load | Data size | Header CRC | Data CRC | Payload entropy | Meaning |
| :--- | :--- | :--- | ---: | :--- | :--- | ---: | :--- |
| `p1` / `p2` (vendor boot0/1) | U-Boot 2016.07-g1c29a95 for n220HfQ, firmware | `0x02800000` | 468,137 | OK | BAD | ~8.0 | Encrypted/protected U-Boot/FIT segment at `0x100000` |
| `p13` / `p14` (`secos`) | `secos-a6de2e4-NT72690_TPV`, standalone | `0x00008000` | 3,931,432 | OK | BAD | ~8.0 | Encrypted ATF/secure stage |
| `p15` / `p16` (`fdt`) | `FDT`, arm64 | `0x0a800000` | 81,792 | OK | BAD | ~8.0 | Encrypted/device-tree payload |
| `p17` / `p18` (`ker0/1`) | `Linux`, kernel | `0x02800000` | 20,504,584 | OK | BAD | ~8.0 | Encrypted current kernel |
| `p21` (`kerupm`) | `Linux`, kernel | `0x02800000` | 19,841,032 | OK | **OK** | ~5.67 | **Plain arm64 Linux 6.1.84-gfd8d77599fee; package `kerupm`** |
| `p19` / `p20` (`fs0/1`) | NFSB | n/a | header only | n/a | n/a | n/a | Identical A/B rootfs headers |

The `Data CRC: BAD` rows are expected if the partition holds a protected image:
the uImage header can carry the pre-encryption/pre-signature CRC while the
partition contains the encrypted payload. The high payload entropy (~8.0) agrees
with encryption or a secure container.

## What is protected and what is not

- The current secure chain images (`p1/p2` U-Boot segment, `p13/p14` ATF,
  `p15/p16` FDT, `p17/p18` kernel) are high-entropy protected payloads.
- `p21` is a **plain, valid arm64 Linux kernel uImage**. Its header and data CRCs
  both verify, the `ARMd` magic is at the arm64 Image offset, and it contains a
  normal Linux 6.1.84 kernel string table.
- `p21` is older (`6.1.84`, built Nov 2024) than the running kernel
  (`6.1.124`, built May 2025). It is not the current A/B secure kernel.

## Slot and boot map

The raw `p9` `misc` partition (DBFG) contains plaintext slot/name strings:

```text
secos0 / secos1     -> p13 / p14
fdt0 / fdt1         -> p15 / p16
ker0 / ker1         -> p17 / p18
fs0 / fs1           -> p19 / p20
apexe0 / apexe1     -> application slots
apexe_ext0/1        -> extended UI slots
tcon0 / tcon1       -> tcon slots
kernel              -> legacy kernel name; package `kerupm` targets p21
```

The same partition also carries the model/firmware string:

```text
TPN256E_V056,rev:191,ChipID:690,SWType:secure,upgrade_xboot:yes,...
```

`SWType:secure` is consistent with the encrypted chain. The `upgrade_xboot:yes`
field is a bootloader-update marker, not a user unlock.

## Vendor boot slots `p1` and `p2`

`p1` and `p2` are identical except for two bytes:

| Offset | `p1` | `p2` | Meaning |
| :--- | :--- | :--- | :--- |
| `0x1a0034` | `0x55` | `0x13` | slot/checksum byte |
| `0x1a0204` | `0x00` | `0x01` | `UMFG` slot value |

The `UMFG` string is at `0x1a0200`; the block around `0x1a0000` is plaintext.
The 24 MiB partitions contain the encrypted U-Boot/FIT segment at `0x100000`
(size `468,137`), a plaintext slot block at `0x1a0000`, and a 552-byte block
near `0xe7ee00`. They are two boot slots, selected by the `UMFG` value.

The eMMC boot areas `mmcblk0boot0` and `mmcblk0boot1` are identical and report
`force_ro=1`, `ro=1`. There is not yet a writable second boot slot.

## The kerupm lead

`p21` is the only plain executable boot image. The package identifies it as
`kerupm` (kernel upgrade manager), target `/dev/nvt-part-name/kerupm`, with no
260-byte component trailer. The likely hypotheses are:

1. The vendor update path boots it as a kernel upgrade manager.
2. It is a fallback kernel used by an update/recovery path.
3. It is not selected in normal boot at all.

If the bootloader can boot `p21` and does not apply the same signature policy,
it is the most plausible route to a custom early boot stage. It is not proven,
and the old kernel may not match the current rootfs/modules. Do not write `p21`
or the boot config before the recovery gate is met. See [update package
map](29-update-package-map.md).

## Boot metadata structures

The `p9` `misc` partition holds plaintext boot metadata. Its structures are:

| Offset | Magic | Meaning |
| ---: | :--- | :--- |
| `0x0` | `DBFG` | partition metadata header: version `1`, values `1`, `1`, `2` |
| `0x400` | `PPCH` | first partition-control table |
| `0xa00` | `PPCH` | second partition-control table |
| `0x1000` | `FWVR` | firmware/model record: `TPN256E_V056,rev:191,...` |
| `0x1200` | `NVHC` | boot-area 0 hash/partition table |
| `0x2400` | `NVHC` | boot-area 1 hash/partition table |
| `0x3600` | `UPST` | upgrade/update state |
| `0x3e10` | n/a | last upgrade package name (`...TPN256E_V056.002.127.021...`) |

Each `PPCH` entry is 60 bytes:

```text
offset  size  field
+0x00   16    name
+0x10   32    device or path
+0x30    4    offset (little-endian)
+0x34    4    flag
+0x38    4    slot (0/1)
```

The `PPCH` tables are per-slot: the first has slot `0`, the second slot `1`.
They map the boot names to devices and, for `uboot`/`vertbl`, to offsets inside
`p1/p2`:

```text
uboot   -> /dev/nvt-part-name/boot0   offset 0x00100000
vertbl  -> /dev/nvt-part-name/boot0   offset 0x00e7ee00
secos   -> /dev/nvt-part-name/secos0
fdt     -> /dev/nvt-part-name/fdt0
kernel  -> /dev/nvt-part-name/ker0
fs      -> /dev/nvt-part-name/fs0
apex    -> /dev/nvt-part-name/apexe0
apext   -> /dev/nvt-part-name/apexe_ext0
```

The `NVHC` blocks repeat the same slot map for `emmc_boot0` and `emmc_boot1`,
including `secos0/1`, `ker0/1`, `fdt0/1`, `fs0/1`, `apexe0/1`,
`apexe_ext0/1`, plus `bflag` and `misc`. The first `NVHC` entry carries an
XBoot hash beginning `c0358135...`. These are hash/partition maps, not a
private key.

The `p1/p2` slots contain three plaintext structures at fixed offsets:

| Offset | Magic | Meaning |
| ---: | :--- | :--- |
| `0x100000` | uImage | encrypted U-Boot/FIT segment |
| `0x1a0000` | `STBC` | boot-control block; slot/`UMFG` state |
| `0x1a0200` | `UMFG` | slot marker (`p1=0`, `p2=1`) |
| `0xe7ee00` | `VTBL` | verification table (`0x224` bytes; signature/hash blob) |

`STBC` fields include version `1`, size `0x64`, slot count `2`, and a byte at
`0x34` that differs between the slots (`p1=0x2d`, `p2=0x0b`). The `UMFG` slot
byte is at `0x1a0204`. The `VTBL` block is identical in `p1` and `p2`; it is
the verification table for the protected images, not a writable slot.

## What the metadata says

- The normal A/B path is `secos0/1` -> `fdt0/1` -> `ker0/1` -> `fs0/1`.
- The `p21` `kerupm` image is not in the `PPCH`/`NVHC` `kernel` map; that map
  resolves `kernel` to `ker0/ker1`. `p21` therefore sits outside the normal
  A/B boot map; the package identifies it as the update kernel.
- The `VTBL` signatures, the `NVHC` XBoot hash, and the encrypted U-Boot/FIT
  segment are the secure-boot chain. Changing `STBC`/`UMFG` alone would select
  between the two identical stock slots, not a custom image.
- The `UPST` block and the old package name in `p9` may indicate the last
  upgrade/recovery state. They are the next place to look for how `p21` is
  selected.

## Next probes

1. Parse `PPCH` and `NVHC` programmatically; map each name to a partition and
   slot, and find the `bflag`/`misc` semantics.
2. Inspect the `VTBL` header and the plaintext FIT metadata around the
   encrypted U-Boot segment; find the verification entry list and what it
   covers.
3. Determine whether `p21` is reachable through the `UPST`/`bflag`/`misc`
   recovery state, and whether it is verified.
4. Establish the recovery path before any write: full eMMC/boot-area restore,
   eMMC ISP/JTAG, or a proven second boot slot.
5. Only then test whether `p21` can be booted or replaced.

## Safety

- Read-only: no partition or boot-area writes.
- Raw `p9`, `p11`, and `p36` stay in `dist/`; the NVM and pstore can contain
  device identity and are not published.
- The eMMC boot areas are write-protected and have no proven restore.
- No DRM/Widevine work.
