# Testing

The suite is standard-library `unittest`; `requests` is the only runtime
dependency.

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover tests -v
```

Current coverage (67 tests):

| Test file | Covers |
| :--- | :--- |
| `test_ambilight_controller.py` | Color parsing, telemetry cache, LED validation. |
| `test_autoroot_usb.py` | Payload validation, one-line autoscript, staging, manifest, required steps. |
| `test_channel_map_tool.py` | CRC-16/MODBUS, factory map verification, bit-identical rebuild. |
| `test_edid_tool.py` | EDID CRC32 and tamper detection. |
| `test_firmware_fetch.py` | Support-page link extraction and candidate filename generation. |
| `test_firmware_parse.py` | TIMG/PIMG header parsing and component extraction. |
| `test_jointspace_client.py` | HMAC signature, mocked network calls, key sequence. |
| `test_deep_probe.py` | Redaction and the read-only command allowlist. |
| `test_bootchain_dump.py` | Read-only item selection, alignment, and dry-run behavior. |
| `test_bootchain_inspect.py` | uImage header/data CRC parsing, embedded images, entropy, markers. |
| `test_boot_metadata.py` | `PPCH` entries, `STBC` slot, `VTBL` length, magic scanning. |
| `test_emmc_backup.py` | Read-only full eMMC backup syntax and target-safety contract. |
| `test_nfsb_raw_mount.py` | Raw NFSB mount helper syntax, usage, and contract. |
| `test_persist_root.py` | Installer hook detection, embedded script syntax, `/swdl` wrapper, no USB dependency. |
| `test_stage_usb.py` | SAM canary staging and CRC verification. |
| `test_uboot_nvm_tool.py` | Dual CRC32, factory verification, bit-identical round-trip. |

## What is not in CI

Hardware tests are documented, not faked:

- USB autoroot on a cold-boot TV.
- Persistent `customer_env.sh` or `/swdl/telnet/telnetd` hook across a reboot.
- SAM NVM/EDID write.
- Serial capture and electrical measurements.
- Runtime raw SquashFS mount of a live NFSB partition. CI checks the helper
  syntax and usage only.

When you run a hardware test, add a short redacted log under `evidence/` and
update `evidence/README.md`.

## Manual checks

```bash
python3 -m compileall -q tools tests
sh -n payloads/autoroot.sh payloads/persist_root.sh payloads/nfsb_raw_mount.sh payloads/emmc_backup.sh
sh -n tools/usb_prep.sh tools/bootstrap/bootstrap.sh
```

## Adding a test

- Use `unittest`, not pytest-only features.
- Use `tempfile` for staging/extraction tests; do not write into the repo.
- Keep fixtures small and synthetic. Do not commit real device dumps or
  identifiers.
- If a test needs a hardware fact, encode the format/expectation, not the
  device's private data.
