# File formats

Status: formats below are verified against the research package and factory
dumps. Keep vendor files out of the public tree.

## `TIMG` / `PIMG` / `NFSB`

| Structure | Size | Key fields |
| :--- | :--- | :--- |
| `TIMG` header | `0x120` | magic `TIMG`, 64-bit payload length at `+0x08`, 16-byte MD5 at `+0x10` |
| `PIMG` header | `0x488` | magic `PIMG`, 64-bit payload length at `+0x08`, 16-byte MD5 at `+0x10`, name at `+0x20`, target at `+0x30`, compression at `+0x70`, flags at `+0x84` |
| `NFSB` header | `0x1000` | SHA-256 + RSA-2048 secure-filesystem wrapper; strip to reach SquashFS |

`enc=gzip` is a normal gzip stream. The container/component MD5 is not an
RSA/ECDSA signature. See [firmware container](../research/03-firmware-container-timg-pimg-nfsb.md).

Tool: `tools/firmware/parse_timg.py`.

## U-Boot NVM (`nvm_ubootdat.data`)

| Offset | Field |
| :--- | :--- |
| `0x00` | outer CRC32 LE over `0x04..EOF` |
| `0x04` | partition ID (`9`) |
| `0x08` | header size (`0x24`) |
| `0x24` | inner CRC32 LE over `0x28..EOF` |
| `0x28` | payload sub-header |
| `0x2C` | null-delimited `key=value` strings |
| EOF | `0x1F64` (8,036 bytes) |

Tools: `tools/uboot_nvm_tool.py`.

## EDID (`nvm_edid.data`)

932 bytes. Outer CRC32 LE at `0x00` over `0x04..EOF`. Partition ID 50 (`0x32`)
at `0x04`. Tools: `tools/edid_tool.py`.

## `chanLst.bin`

102-byte index for `ChannelMap_100`:

- `0x00`: version `100`.
- `0x04`–`0x11`: sync/padding.
- records: 32-bit LE length, null-terminated relative path; files carry a
  16-bit LE CRC-16/MODBUS, directories end in `/`.
- CRC-16/MODBUS: poly `0x8005` reflected, init `0xFFFF`, reflected in/out,
  xor-out `0`.

Tool: `tools/channel_map_tool.py`. See [channel maps](../research/10-channel-maps.md).

## `UMFG` and `DEBUG_FUNC_LEVEL`

The vendor `board/run.sh` reads `/dev/nvt-part-name/boot0` (vendor partition
`mmcblk0p1`) at `1704448` (`0x1A0200`):

```text
+0x00  "UMFG"
+0x04  uint32 LE DEBUG_FUNC_LEVEL (run.sh exports value & 7)
```

The tested p1 slice is `UMFG\x00\x00\x00\x00`; p2 is `UMFG\x01\x00\x00\x00`.
The eMMC boot partitions (`mmcblk0boot0`/`boot1`) are a different device and
contain XBoot. The exact XBoot `uart mode:0` input is still open; see
[dead ends](../research/12-verified-findings-and-dead-ends.md).
