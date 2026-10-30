# Channel maps

Status: **VERIFIED** against the factory export and `chanLst.bin`.

## Layout

```text
PhilipsChannelMaps/
└── ChannelMap_100/
    ├── ChannelList/
    │   ├── chanLst.bin
    │   ├── channellib/
    │   │   ├── DVBC.xml
    │   │   └── DVBT.xml
    │   └── s2channellib/
    │       ├── DVBS.xml
    │       ├── DVBSall.xml
    │       ├── FLASH_FSTSECTS
    │       ├── FLASH_SGTSECTS
    │       ├── FLASH_TKGSSECTS
    │       ├── mgr_satset.db
    │       └── mgr_tkgs_manage
    └── usr/
```

The factory `DVBC.xml`, `DVBT.xml`, `DVBS.xml`, and `DVBSall.xml` are 66-byte
empty XML documents. The `usr/` directory is empty in the factory export.

## `chanLst.bin`

The 102-byte header binds the model and the files:

```text
0000: 00 00 64 00 ff ff ff ff ff ff ff ff ff ff 00 00
0010: 00 00 0d 00 00 00 35 35 50 55 53 38 30 30 30 2f  | ......55PUS8000/
0020: 31 32 00 09 00 00 00 44 56 42 54 2e 78 6d 6c 00  | 12...DVBT.xml.
0030: 2a 9a 09 00 00 00 44 56 42 43 2e 78 6d 6c 00 2a  | *.....DVBC.xml.*
0040: 9a 0f 00 00 00 2f 73 32 63 68 61 6e 6e 65 6c 6c  | ...../s2channell
0050: 69 62 2f 00 0c 00 00 00 44 56 42 53 61 6c 6c 2e  | ib/....DVBSall.
0060: 78 6d 6c 00 2a 9a                                | xml.*.
```

- `0x00`: channel map version `100`.
- `0x04`–`0x11`: fixed sync/padding.
- Then repeated records: 32-bit little-endian length, a null-terminated relative
  path, and for files a 16-bit little-endian **CRC-16/MODBUS** of the file.
- Directories end in `/` and have no CRC.

## CRC-16/MODBUS

- Polynomial `0x8005`, reflected `0xA001`.
- Initial value `0xFFFF`.
- Reflected input/output, XOR-out `0`.
- Stored little-endian.

Running the CRC over the 66-byte XML yields `0x9A2A`, stored as `2a 9a`.

## Tool

```bash
python3 tools/channel_map_tool.py verify samples/channel-maps/ChannelMap_100
python3 tools/channel_map_tool.py dump   samples/channel-maps/ChannelMap_100
python3 tools/channel_map_tool.py recalculate samples/channel-maps/ChannelMap_100
```

The public sample keeps only the small `chanLst.bin` and XML files. The
multi-megabyte `FLASH_*` sector tables and satellite databases are vendor data
and are not included.

## The `usr/` idea

The factory export creates an empty `ChannelMap_100/usr/`. It is a tempting
traversal canary, but no code-execution path through it is verified. Treat it as
an open research question, not a vulnerability. See
[dead ends](12-verified-findings-and-dead-ends.md).
