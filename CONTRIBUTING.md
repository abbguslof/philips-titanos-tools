# Contributing

Thanks for helping improve the research and the tooling.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m unittest discover tests
```

Python 3.8+ is supported. The tests use the standard library `unittest`; the
only runtime dependency is `requests` (used by the JointSpace client).

## Repository rules

- **No real device data.** Serials, MACs, SSIDs, PINs, pairing credentials, home
  IPs, workstation usernames, private keys, and raw captures are not accepted.
  Use documentation ranges (`192.0.2.0/24`), `02:00:00:00:00:00`, and
  `SERIAL`/`<TV_IP>` placeholders.
- **No vendor firmware.** Do not commit `.pkg`, `.zip`, SquashFS, extracted
  rootfs, or other proprietary vendor payloads. Document how to obtain and
  verify them instead.
- **No third-party binaries without notices.** If you add a binary, add its
  license/source to `THIRD_PARTY_NOTICES.md`.
- **Keep evidence small.** Prefer a 32-byte slice, a short log, or a hash over a
  multi-megabyte dump.
- **Label status.** Use `VERIFIED`, `TESTED-NEGATIVE`, `INFERRED`, or `OPEN` in
  research docs. Do not mix a design idea into a verified section.

## Code style

- Python: standard library first; keep CLI tools usable with no install step
  beyond `requests`.
- Shell: POSIX `sh` where possible; the TV rootfs uses BusyBox ash. Avoid
  `bash`-only features in payloads.
- Do not add comments that restate the code. Explain non-obvious hardware or
  boot-order constraints.
- Keep the payload free of `pkill` and unconditional firewall flushes.

## Tests

Add a test when you add parsing, checksum, path, or staging logic. Hardware
tests cannot run in CI; document what was run on hardware and attach a redacted
log under `evidence/`.

```bash
python3 -m unittest discover tests
python3 -m compileall -q tools tests
sh -n payloads/autoroot.sh payloads/persist_root.sh
```

## Pull requests

1. Describe the hardware/firmware used and whether the change was verified.
2. Include the test output.
3. Confirm that no secrets or real identifiers are included.
4. Update the relevant doc and the evidence index.
5. Keep commits focused; prefix with `docs:`, `tools:`, `payloads:`, or `tests:`.

By contributing you agree that your original code and documentation are
licensed under the MIT License. Third-party material must keep its own license.
