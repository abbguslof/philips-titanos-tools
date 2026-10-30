# Samples

Small, non-identifying factory files used by the tests and documentation.

| Path | What it is |
| :--- | :--- |
| `nvm/nvm_ubootdat.data` | Factory NVM environment sample. Dummy MAC and placeholder production code. |
| `nvm/nvm_edid.data` | Factory EDID sample. |
| `channel-maps/ChannelMap_100/ChannelList/chanLst.bin` | 102-byte channel index. |
| `channel-maps/ChannelMap_100/ChannelList/channellib/*.xml` | Empty 66-byte DVB XMLs. |
| `channel-maps/ChannelMap_100/ChannelList/s2channellib/*.xml` | Empty 66-byte DVB XMLs. |
| `identify/update.html`, `identify/updatecracked.html` | Legacy update-assistant samples with placeholder serials. |

**Not included:** full firmware packages, extracted rootfs/application
filesystems, multi-megabyte `FLASH_*` sector tables, satellite databases, raw
logs, packet captures, or real device identifiers.

The NVM sample is a format example, not a substitute for your own factory
backup. Verify with:

```bash
python3 tools/uboot_nvm_tool.py verify samples/nvm/nvm_ubootdat.data
python3 tools/edid_tool.py verify samples/nvm/nvm_edid.data
python3 tools/channel_map_tool.py verify samples/channel-maps/ChannelMap_100
```
