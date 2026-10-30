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

## Acquisition

The package used for this research is not redistributed. See
[firmware acquisition](../guides/firmware-acquisition.md) for the historical
curl process, the official support-page path, and the recorded hashes.
