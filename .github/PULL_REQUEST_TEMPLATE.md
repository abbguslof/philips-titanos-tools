## What changed

<!-- One or two sentences. -->

## Verification

- [ ] `python3 -m unittest discover tests` passes.
- [ ] `python3 -m compileall -q tools tests` passes.
- [ ] `sh -n payloads/autoroot.sh payloads/persist_root.sh` passes.
- [ ] Hardware-tested? If yes, state model/firmware and attach a redacted log under `evidence/`.

## Safety

- [ ] No real serial, MAC, SSID, IP, PIN, pairing credential, or private key.
- [ ] No vendor firmware or extracted vendor filesystem.
- [ ] The change preserves the documented restore path.
- [ ] Docs and `evidence/README.md` are updated if behaviour or evidence changed.
