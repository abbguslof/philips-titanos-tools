# Firmware extraction

Status: **VERIFIED** against the research package. The package is not included.

## Inspect the container

```bash
python3 tools/firmware/parse_timg.py PH_2K25_ALL_EU_NT72690_TPN256E_V056.002.236.191_upgrade.pkg
```

Example output shape:

```text
package: PH_...pkg
size:    1530220984 bytes
payload: ... bytes, MD5 ...
components: 32

 #  name             compression      length  target                       flags
 0  xboot            enc=none          ...     /dev/nvt-part-name/boot0     ...
...
```

Verify the whole-container MD5:

```bash
python3 tools/firmware/parse_timg.py PH_...pkg --verify
```

This checks the `TIMG` MD5 over the payload. It does **not** verify the inner
`NFSB` RSA/SHA-256 signature; that is the secure-boot layer.

## Extract one component

```bash
python3 tools/firmware/parse_timg.py PH_...pkg --extract fs0 -o fw/extracted
```

The tool:

1. seeks to the component payload and decompresses `enc=gzip` if needed;
2. verifies the `PIMG` MD5 **after decompression** (the MD5 covers the
   decompressed component payload, not the gzip stream);
3. if the result starts with `NFSB`, strips the 4,096-byte header and writes a
   `.sqsh`;
4. never executes the payload.

Then mount/extract the SquashFS:

```bash
unsquashfs -d fw/rootfs fw/extracted/00-fs0.sqsh
```

The rootfs and application partitions use SquashFS 4.0 LZO. `ap0` is the large
`mtd_apexe` partition; `apext0` is the extended UI/Opera partition.

## Why not use hardcoded offsets?

Early notes used `dd` offsets (`0x47D8CB2`, `0x1FAFA52C`) for one specific
package. They are brittle and easy to get wrong. The parser walks the actual
`TIMG`/`PIMG` headers and validates sizes and MD5s, so it works across packages
with a different component order.

## What you get

- `fs0` -> rootfs (`/`), read-only SquashFS.
- `ap0` -> `mtd_apexe`, Titan OS application/browser runtime.
- `apext0` -> `apexe_ext`, Opera/UI extensions.
- `frcfw` -> FRC/local-dimming ISP firmware (Ext2, not SquashFS).
- bootloader/partition images -> raw `PIMG` payloads.

The extraction does not decrypt or bypass `NFSB`; it only strips the header for
static inspection. Do not assume a modified filesystem can be flashed back.

## Legal and safety

Keep vendor filesystems out of the public repository. `.gitignore` excludes
`fw/`, `*.pkg`, `*.sqsh`, `*.img`, `*.gz`, and `*.bin`. The `samples/` tree
contains only small, non-identifying files.
