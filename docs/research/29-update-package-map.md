# Update package map and the plain `kerupm` kernel

Status: **VERIFIED (local package comparison)** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`. No TV writes. The vendor package is local-only and
is not published.

> The 2026-11-14 analysis in [research/30](30-update-path-2026-11-14.md) maps
> the burner checks and the prepared dump-only test package.

Phase B also mapped the firmware package to the live partitions. The package
exposes one **plain, unsigned-at-component-level** kernel.

## Method

- `tools/firmware/parse_timg.py` listed the package and extracted selected
  components.
- The extracted components were compared byte-for-byte with the read-only
  `p9`/`p1`/`p2`/`ker0`/`fdt0`/`secos0`/`xboot`/`p21` dumps.
- No TV partition was written, mounted, or modified.

## The live boot chain is the package

| Package component | Target | Package size | Live match |
| :--- | :--- | ---: | :--- |
| `xboot` | `/dev/mmcblk0boot0` | 390,488 | exact first 390,488 bytes of `boot0` |
| `uboot` | `/dev/nvt-part-name/boot0` | 468,461 | exact at `p1/p2 + 0x100000` |
| `vtbl` | `/dev/nvt-part-name/boot0` | 556 | live `VTBL` is the same length but different bytes |
| `secos0` | `/dev/nvt-part-name/secos0` | 3,931,756 | exact at `p13/p14` |
| `fdt0` | `/dev/nvt-part-name/fdt0` | 1,179,648 | exact at `p15/p16` |
| `ker0` | `/dev/nvt-part-name/ker0` | 20,504,908 | exact at `p17/p18` |
| `stbc` | `/dev/mmcblk0boot0` | 65,796 | exact at `boot0 + 0xbb800` |
| `pptbl0/1` | `/dev/nvt-part-name/misc` | 1,536 each | exact `p9 + 0x400` / `+0xa00` |
| `vinfo` | `/dev/nvt-part-name/misc` | 512 | exact `p9 + 0x1000` |
| `upst` | `/dev/nvt-part-name/misc` | 512 | live `p9 + 0x3600` is runtime state |
| `bflag` | `/dev/nvt-part-name/misc` | 512 | not found byte-exact in the live dumps |
| `kerupm` | `/dev/nvt-part-name/kerupm` | 19,841,096 | **exact at `p21`** |

The secure packages are uImages with a **260-byte trailer** after the uImage
data. For example, `ker0` is 20,504,908 bytes while its uImage header + data are
20,504,648; `secos0` is 3,931,756 vs 3,931,496. The uImage data CRCs therefore
fail on the stored bytes: the header CRC covers the plaintext image, and the
trailer carries the signature/protection data. `uboot` has the same 260-byte
trailer. This explains the earlier CRC results without assuming encryption of
every byte.

`fdt0` is larger than its uImage data by about 1 MiB; the FDT component carries
additional data beyond the small uImage payload. It is still exact at the live
partition.

The live `VTBL` and `upst` differ from the package templates. `upst` is a
runtime state record; the `VTBL` may be generated or updated on the device. The
live `bflag` was not found byte-exact; its runtime location and semantics are
still unknown.

## The `kerupm` lead

`kerupm` is the **kernel upgrade manager** image:

- target: `/dev/nvt-part-name/kerupm` (the live `p21` partition);
- package and live bytes are identical;
- it is a **plain uImage** with valid header and data CRC;
- it has **no 260-byte signature trailer**;
- it is Linux `6.1.84-gfd8d77599fee` (the upgrade kernel), older than the
  running `6.1.124` main kernel;
- the package also carries `sys_run` (~5.2 MB) and `eburner` (~22.5 MB), both
  targeting `/dev/null`, plus `pre_install` and `part_tbl`.

The package container and PIMG components are **MD5-only**; the inner NFSB
filesystems are RSA/SHA-256. The `kerupm` component has no component-level
signature of its own. Whether the update loader verifies `kerupm` through the
`VTBL`, `stbc`, or another check is **unknown**.

## The update environment

The package also carries a RAM-only update environment:

| Component | Shape | Target | Notes |
| :--- | :--- | :--- | :--- |
| `eburner` | plain Linux/arm64 uImage, 22,566,984 | `/dev/null` | no 260-byte trailer; eMMC/STBC/FDT drivers |
| `sys_run` | gzip tar, 5,176,607 -> 19,005,440 | `/dev/null` | `run.sh`, `nvt_eburner`, `ndp_preinit.ko`, `ndp_gfx.ko` |
| `nvt_eburner` | static ARM32 ELF, 721 KiB | inside `sys_run` | the eMMC burner |

`part_tbl` is a plaintext partition list. It includes `kerupm;49152` (24 MiB)
and the A/B `ker0/ker1`, `secos0/1`, `fdt0/1`, `fs0/1`, `apexe0/1`,
`apexe_ext0/1`, `misc`, `devcfg`, `nvm_dat`, and `boot0/1` entries. The
`kerupm` component and the partition table agree on the 24 MiB target.

`sys_run/run.sh` is executed in the update environment. It installs the two
kernel modules, copies `stty`, then runs:

```sh
nvt_eburner $1
echo "update finish ,system reboot !!!"
reboot
```

`nvt_eburner` contains the update logic: `nvt_eburner_verify_whole_image`,
`nvt_eburner_md5_part_verify`, `md5sum`, `md5tbl`, `Extract md5tbl`, `Verify
image failed`, partition-write callbacks for `xboot`, `stbc`, `vtbl`, `fdt`,
`ker`, boot-flag writes, and boot-argument/FDT updates. The strings show
**MD5-based verification**; no RSA/SHA verification strings were observed in
this binary.

The update environment components target `/dev/null`. The package's `kerupm`
component targets the persistent `p21` partition.

### The trust gap

- The update environment (`eburner` + `sys_run` + `nvt_eburner`) is plain at the
  component level.
- The package container and PIMG components are MD5-only.
- The NFSB filesystems remain RSA/SHA-256 and are not modified.
- `sys_run/run.sh` runs as root before the burner.
- The normal A/B secure chain is not involved in the RAM update environment.

This makes a **modified update package** a plausible update-mode code-execution
path. It is a hypothesis until a controlled test is run.

### Controlled test

The safest first test is not a flash. Modify only `sys_run/run.sh` to:

1. dump `/dev/mmcblk0`, `mmcblk0boot0` and `mmcblk0boot1` to the mounted USB
   filesystem;
2. write SHA-256 hashes;
3. skip `nvt_eburner`;
4. `sync` and `reboot`.

Then rebuild only the `sys_run` PIMG component MD5 and the TIMG container MD5,
keeping every NFSB component and every secure component unchanged. If the
update loader accepts the package, the update environment runs as root and
produces a full eMMC backup without flashing anything. If it rejects the
package, no partition was written.

Do this only on the owned 8000 and only after the eMMC/recovery gate exists.
The update trigger/loader is still unknown: USB, OTA, `upst`/`bflag`, or the
vendor update process.

## Why this matters

The normal A/B boot path is protected:
`uboot` -> `secos0/1` -> `fdt0/1` -> `ker0/1` -> `fs0/1`, with signatures and
verification tables. The upgrade path is different: the vendor package carries
a plain `kerupm` kernel and update payloads target `/dev/null` (loaded into RAM
by the update process).

If the update loader boots `kerupm` without a separate signature check, a
modified `kerupm` package is a potential update-mode code-execution path. That
would not require breaking the secure A/B slots; it would use the vendor's own
upgrade mechanism. Treat it as a hypothesis until tested.

## Risks and gates

- Modifying a vendor update package and booting/flashing it is **boot-chain
  risk**. A bad package can leave the TV unbootable.
- The NFSB components must remain unchanged and valid; only the plain
  `kerupm` (and maybe the update-side components) is a candidate.
- The update trigger is not mapped: USB, SAM, OTA, `upst`/`bflag`, or the
  vendor loader. The historical `upgrade_loader` evidence is not a working
  loader.
- Do not test on the 8450 or another owner's TV.
- Do not test on the 8000 until Phase R has a verified eMMC/boot-area restore.

## Next probes

1. Determine the update trigger and loader path: `pre_install`, `part_tbl`,
   `sys_run`, `eburner`, `upst`, `bflag`, and the vendor package delivery.
2. Reverse `nvt_eburner`'s MD5 table and component checks; confirm that a
   rebuilt `sys_run` is accepted and whether `kerupm` is covered.
3. Build the **non-destructive** `sys_run/run.sh` package that only dumps the
   eMMC/boot areas to USB and skips the burner. Recompute only the
   `sys_run`/TIMG MD5s; keep NFSB and secure components untouched.
4. If the update environment runs it, you get a full eMMC backup and a root
   update environment. That is the Phase R gate.
5. Then test a modified `kerupm` or boot flag only after the restore is proven.
6. If the package is rejected, fall back to the secure-chain/U-Boot map.

## Safety

- The vendor package remains local and is not committed.
- The extracted components are under `/tmp` and `dist/` and are not published.
- No TV partition was written.
- No DRM/Widevine work.
