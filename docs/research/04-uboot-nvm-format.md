# U-Boot-style NVM format (`nvm_ubootdat.data`)

Status: **VERIFIED** on hardware (read, modify, dual CRC32, SAM write, reboot).

The TV calls this "U-Boot NVM", but the boot chain is XBoot (see
[boot chain](01-boot-chain-xboot-atf.md)). The file is an 8,036-byte
environment container on partition **p9**, exported by SAM as
`SAM/nvm_ubootdat.data`.

## Layout

```text
+---------------------+--------------------------------------------------------+
| Offset              | Field                                                  |
+---------------------+--------------------------------------------------------+
| 0x0000 - 0x0003     | Outer CRC32 (uint32 LE), covers 0x0004..EOF            |
| 0x0004 - 0x0007     | Partition type ID (uint32 LE = 9)                      |
| 0x0008 - 0x000B     | Header size (uint32 LE = 0x24 = 36)                    |
| 0x000C - 0x0023     | Reserved / zero padding                                |
| 0x0024 - 0x0027     | Inner CRC32 (uint32 LE), covers 0x0028..EOF            |
| 0x0028 - 0x002B     | Payload sub-header (0x2cf8db9c on the factory dump)    |
| 0x002C - 0x0679     | Null-terminated ASCII `key=value` environment strings  |
| 0x067A - 0x1F63     | Zero padding to 8,036 bytes                            |
+---------------------+--------------------------------------------------------+
```

## Dual CRC32

The container uses standard IEEE 802.3 CRC32 (`zlib.crc32`, polynomial
`0xEDB88320`, initial 0, no salt):

```python
inner = zlib.crc32(data[0x28:]) & 0xFFFFFFFF   # stored at 0x24
outer = zlib.crc32(data[0x04:]) & 0xFFFFFFFF   # stored at 0x00
```

The outer CRC covers the inner CRC, so recalculate inner first, then outer.
`tools/uboot_nvm_tool.py` verifies, dumps, edits, diffs, and rebuilds the file.

```bash
python3 tools/uboot_nvm_tool.py verify samples/nvm/nvm_ubootdat.data
python3 tools/uboot_nvm_tool.py dump   samples/nvm/nvm_ubootdat.data
```

## Observed variables

The factory dump contains 68 variables. Examples:

```ini
board_id=NT72690
board_name=715GD542
model_name=55PUS8000/12
uart_mode=1
watch_dog_timeout=1
mds_mode=0
OP1=160 000 020 068 009 037 008 236
OP2=147 004 002 148 194 036 024 000
OP3=032 014 000 098 032 177 197 059
OP4=255 000 000 000 000 000 001 012
CSM_Production_code=TW123456789123
```

`uart_mode=1` in NVM does **not** change XBoot's `uart mode:0`; XBoot does not
use this variable. `mds_mode=1` does **not** unlock JointSpace engineering
routes; the `tvtype: consumer` lock is in userspace. Both were tested.

## Hardware write path

SAM **`Download from USB` -> `NVM copy`** reads `SAM/nvm_ubootdat.data`,
verifies both CRC32 layers, and writes partition p9. This was verified on
hardware with `canary_test=1` and `bootdelay=5`; the TV displayed "Done" and
rebooted cleanly. `bootdelay=5` is inert because there is no interactive
U-Boot prompt.

The factory sample in `samples/nvm/nvm_ubootdat.data` uses a dummy MAC and
placeholder production code. Keep a pristine backup before any write.

See the [SAM guide](../guides/sam-download-from-usb.md) and the
[restore guide](../guides/restore-to-stock.md).
