# Firmware container: `TIMG`, `PIMG`, `NFSB`

Status: **VERIFIED** by parsing the full `PH_2K25_ALL_EU_NT72690_TPN256E_V056.002.236.191_upgrade.pkg`
(1.53 GB) and by reading the vendor update code.

## The package is a Novatek `TIMG` container

```text
+----------------------+------------------------------------------------------+
| Offset               | Field                                                |
+----------------------+------------------------------------------------------+
| 0x00                 | magic "TIMG"                                         |
| 0x08                 | 64-bit payload length                                |
| 0x10                 | 16-byte MD5 of the payload (0x120..EOF)              |
| 0x120                | first PIMG header                                    |
+----------------------+------------------------------------------------------+
```

Each component has a **1,160-byte (`0x488`) `PIMG` header**:

```text
+--------+--------------------------------------------------------------+
| Offset | Field                                                        |
+--------+--------------------------------------------------------------+
| +0x00  | magic "PIMG"                                                 |
| +0x08  | 64-bit payload length                                        |
| +0x10  | 16-byte MD5 of the component's unencrypted payload           |
| +0x20  | component name (for example fs0, ap0, apext0)                |
| +0x30  | target device path / partition                               |
| +0x70  | compression: "enc=none" or "enc=gzip"                        |
| +0x84  | flags, for example "DUAL-PART-BURN"                          |
+--------+--------------------------------------------------------------+
```

The package contains **32 components**. The `enc=gzip` payloads are ordinary
gzip streams, not encrypted blobs. Decompressing one yields an **`NFSB`**
secure-filesystem wrapper.

## Two integrity layers, do not mix them up

| Layer | Integrity | What it covers |
| :--- | :--- | :--- |
| `TIMG` whole container | **MD5 only** | Payload from `0x120` to EOF. No RSA/ECDSA container signature was found. |
| `PIMG` component payload | **MD5 only** | The unencrypted component payload. |
| `NFSB` inner filesystem | **SHA-256 + RSA-2048** | The filesystem image inside the 4,096-byte `NFSB` header. |

So the correct statement is: **the container and component integrity are
MD5-only; the filesystems are wrapped in an RSA/SHA-256 `NFSB` header.** Do not
write "the firmware has no signatures" without that qualification.

## `NFSB` and SquashFS

The first `0x1000` bytes of a decompressed `fs0`/`ap0` payload are the `NFSB`
header. Stripping it leaves a standard **SquashFS 4.0 LZO** image:

```bash
# after decompressing the component to fs0.img
dd if=fs0.img of=fs0.sqsh bs=4096 skip=1
unsquashfs -d rootfs fs0.sqsh
```

`ap0` is the 452 MB application partition (`mtd_apexe`), mounted read-only in
userspace through the `nfsb` kernel module. `apext0` is the extended UI/Opera
partition.

> **Runtime note (verified 2026-11-05).** The NFSB verifier is exercised by
> the `nfsb` mount. The inner SquashFS at offset `0x1000` can be mounted
> directly with the normal `squashfs` driver (`losetup` + `mount -t squashfs`)
> on the running TV. This is a runtime read-only/custom-layer path; it does
> not make a modified NFSB image flashable or bootable and does not defeat
> the boot-time verifier. See [runtime NFSB bypass](17-runtime-nfsb-squashfs.md).

## Why this matters for research

- The container is easy to parse without vendor tools: read the `TIMG` header,
  walk the `PIMG` headers, verify MD5, decompress gzip, strip `NFSB`, mount
  SquashFS.
- The MD5-only container means a modified package is not rejected by a
  container signature. The inner `NFSB` RSA/SHA-256 layer is the real secure-boot
  boundary, so do not assume you can reflash a modified rootfs without dealing
  with it.
- The extraction guide uses a parser, not hardcoded byte offsets. See
  [firmware extraction](../guides/firmware-extraction.md).

## `TIMGPKGVER40`: the 2023 Titan OS revision

Status: **VERIFIED** by parsing the shipped `TPN236E_236.006.135.001` package
(43PUS7608/12, 621 MB `autorun.upg`): all 19 component MD5s checked against the
stored payloads. Not yet verified against hardware.

Newer 2023 Titan OS packages replace the layout above:

```text
+----------------------+------------------------------------------------------+
| Offset               | Field                                                |
+----------------------+------------------------------------------------------+
| 0x00                 | magic "TIMGPKGVER40" (12 bytes)                      |
| 0x120                | "PPCH"/vertbl partition table (~0x34C bytes,         |
|                      | 13 name->target entries), variable length            |
| first PIMG           | first component header (0x720 in the reference pkg)  |
| EOF                  | last component payload ends exactly here             |
+----------------------+------------------------------------------------------+
```

There is **no whole-container length/MD5 field**: the component region runs
from the first `PIMG` header to EOF, and components are back-to-back
(`next = header + size + length`). A `PIMG` byte sequence also occurs inside
the vertbl region and inside (encrypted) payloads, so a scanner must validate
candidate offsets by walking the chain to EOF, not by magic alone.

Each component has a **1,120-byte (`0x460`) `PIMG` header**:

```text
+--------+--------------------------------------------------------------+
| Offset | Field                                                        |
+--------+--------------------------------------------------------------+
| +0x00  | magic "PIMG"                                                 |
| +0x04  | 32-bit payload length                                        |
| +0x08  | 16-byte MD5 of the component's *stored* payload              |
| +0x18  | component name (16 bytes: vertbl, xboot, kernel, fs, ap, ...)|
| +0x28  | target device path / partition (32 bytes)                    |
| +0x48  | compression: "none" or "gzip"                                |
+--------+--------------------------------------------------------------+
```

Two differences matter:

- **Every stored payload is vendor-encrypted** with a fixed key — including
  `none`-labelled components (a raw extraction of `kernel` does not start with
  the uImage magic; the decrypted one does). The `compression` field describes
  the state *after* decryption, and the `PIMG` MD5 covers the **stored
  (encrypted)** payload, so MD5 verification succeeds against ciphertext and
  proves nothing about plaintext. The fixed keys are embedded in the vendor
  update library (`libfwup.so` `.data`) and match the keys used by the
  third-party `unixtract` extractor (`github.com/theubusu/unixtract`), which
  performs the decryption.
- After decryption, `fs`/`ap`/`apext` are `NFSB`-wrapped SquashFS 4.0 LZO
  exactly as in the classic layout (`fs` targets `/dev/mmcblk0p16` on this
  package); `kernel`/`fdt`/`uboot`/`secos` are uImages, `bootlogo` a JPEG.

`tools/firmware/parse_timg.py` detects the container magic and supports both
layouts; it carves and MD5-verifies components but does not decrypt.

## Acquisition

The package used for this research is not redistributed. See
[firmware acquisition](../guides/firmware-acquisition.md) for the historical
curl process, the official support-page path, and the recorded hashes.
