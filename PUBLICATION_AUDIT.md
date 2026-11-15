# Publication & Direction Audit

**Date:** 2026-11-09
**Target:** `55PUS8000/12`, chassis `TPA256E`/`TPN256E`, mainboard `715GD542`, firmware `TPA256E_V056.002.236.191`
**Verdict:** **GO** with non-blocking cleanup items

---

## Verdict: GO

The repository is ready for publication with minor non-blocking cleanup items. All critical paths are verified, evidence is properly redacted, and documentation follows the status-label convention.

---

## Blocking Issues (0)

| # | Issue | Impact | Fix |
| :-- | :--- | :--- | :--- |
| - | None | - | - |

---

## Non-Blocking Cleanup Items (5)

| # | Issue | Location | Severity | Recommendation |
| :-- | :--- | :--- | :--- | :--- |
| 1 | `ubuntu-latest` CI runner not pinned | `.github/workflows/ci.yml:13` | Low | Pin to `ubuntu-24.04` for reproducibility |
| 2 | BusyBox provenance incomplete | `THIRD_PARTY_NOTICES.md:6-17` | Low | Add Debian build date/mirror for 1.35.0 armhf static binary |
| 3 | Sample file lacks change note | `samples/identify/updatecracked.html` | Low | Add comment noting placeholder serial `TW01234567` vs stock format |
| 4 | `pyproject.toml` package name mismatch | `pyproject.toml:6` | Low | `philips-titanos-tools` vs repo `philips-titan-tools` (cosmetic) |
| 5 | `__pycache__` in grep output | N/A | Info | Consider `.gitignore` enforcement in CI |

---

## Direction Audit Findings

### ✅ Repository Drift: Controlled

- **Status labels are load-bearing and consistent.** All 17 research documents carry VERIFIED/TESTED-NEGATIVE/INFERRED/OPEN labels.
- **README tables match research docs.** The "What is verified" table in README.md aligns with docs/research/12-verified-findings-and-dead-ends.md.
- **No scope creep.** Private OS work explicitly called out as out of scope (README.md:28, docs/README.md:60).

### ✅ Tool Safety Features: Present

| Tool | Safety Mechanism | Location |
| :--- | :--- | :--- |
| `autoroot_usb.py` | SHA-256 manifest, read-only remount verification, `--no-verify` flag | `tools/autoroot_usb.py:335-433` |
| `uboot_nvm_tool.py` | Dual CRC32 verify subcommand, inner/outer checksum validation | `tools/uboot_nvm_tool.py:292-293` |
| `channel_map_tool.py` | CRC-16/MODBUS verify subcommand | `tools/channel_map_tool.py:256-258` |
| `edid_tool.py` | Outer CRC32 verify subcommand | `tools/edid_tool.py:100-102` |
| `parse_timg.py` | `--verify` flag for whole-container MD5 | `tools/firmware/parse_timg.py:178` |

**Gap:** No `--dry-run` mode for write operations (NVM/channel-map writes). Documented as hardware-dependent in guides.

### ✅ README vs SECURITY.md: Consistent

- Both claim **physical USB access required** (README.md:19, SECURITY.md:8-16)
- Both claim **no remote exploit** (README.md:22, SECURITY.md:18)
- Both reference **restore path** (README.md:198, SECURITY.md:98-99)
- CDP `:7788` exposure documented in both as "local debug surface, not root path" (README.md:48, SECURITY.md:59-63)

---

## Ranked Access Roadmap

Converted from `docs/research/12-verified-findings-and-dead-ends.md` open questions:

| Priority | Question | Domain | Effort | Risk | Notes |
| :------: | :--- | :--- | :--- | :--- | :--- |
| **1** | Exact source of XBoot's `uart mode:0` print | Boot chain | Medium | Low | Vendor script reads UMFG but XBoot still reports mode 0 |
| **2** | Whether future firmware keeps `quick_debug/menu auto` hook | USB autoroot | Low | Medium | Requires firmware update test on hardware |
| **3** | Whether user trust store extendable from USB to defeat `DP_203` | TLS pinning | High | Medium | Would enable HTTPS MITM for `app.titanos.tv` |
| **4** | Whether channel-map import parser has memory-safety bug | Channel maps | High | Medium | Not tested; requires fuzzing `chanLst.bin` parser |
| **5** | Whether v33-only netlink permissions matter to running services | SELinux | Low | Low | `nlmsg_readpriv`, `nlmsg_getneigh` remain denied |
| **6** | Whether to restore `app.titanos.tv` in Pi-hole or keep cloud blocked | Telemetry | Low | Low | User preference; TV otherwise working |
| **7** | Whether eMMC `boot_area` can be switched for recovery | Hardware | Medium | High | Brick risk; requires hardware access |
| **8** | Whether boot-time NFSB verifier bypassable without vendor RSA key | Boot chain | High | High | Runtime raw mount works; boot-time `NVHC` adds more checks |

---

## UNKNOWN List

| # | Unknown | Impact |
| :-- | :--- | :--- |
| 1 | CDP `:7788` LAN reachability without pairing | Attack surface; documented as open |
| 2 | Channel-map `usr/` traversal code-execution path | Potential RCE; not verified |
| 3 | Whether `BrowserIpcPluginClass` exploitable from authorized origin | IPC boundary; inert from plain HTTP |
| 4 | Long-term stability of permissive v33 policy across firmware updates | Maintenance; requires re-build on update |
| 5 | Whether `ndp_logo_seloff_boot.ko` carrier stable across reboots | SELinux; kernel module route works but causes audit log noise |

---

## Evidence Summary

| Category | Count | Status |
| :--- | :--- | :--- |
| Research documents | 17 | All carry status labels |
| Verified findings | 38 | Table in docs/research/12 |
| Dead ends | 24 | Documented with reasons |
| Open questions | 8 | Converted to roadmap above |
| Evidence captures | v1-v7 | Redacted, SHA-256 verified |
| Unit tests | 40 | Pass on Python 3.9/3.11/3.12 |
| Total code lines | ~5,830 | 13 Python + 4 shell files |

---

## Sanitization Check: Detailed Identifier Table

**Result:** All identifiers are documentation values or non-identifying UUIDs.

| file:line | string | looks like MAC/IP/serial/SSID | redacted y/n |
| :--- | :--- | :--- | :--- |
| `samples/nvm/nvm_edid.data:~0x36c` | `93bfc3ab-057e-42ac-a595-2ae89e02073e` | UUID (not MAC/IP/serial/SSID) | N/A |
| `evidence/usb-autoroot/v3-telnetd-listen/net3.txt:3-23` | `0.0.0.0`, `127.0.0.1`, `192.0.2.10` | IP addresses (documentation) | y |
| `evidence/usb-autoroot/v4-shell-uid0/net4.txt:1-2` | `:::` (IPv6 wildcard) | IPv6 wildcard | n |
| `evidence/usb-autoroot/v2-pty-rx/diag.txt` | none | - | - |
| `evidence/usb-autoroot/v3-telnetd-listen/diag3.txt` | none | - | - |
| `evidence/usb-autoroot/v6-regression/net4.txt` | (empty file) | - | - |

**EDID decode:** `samples/nvm/nvm_edid.data` is **not** a standard 128-byte EDID block. It is a 932-byte NVM wrapper containing:
- Bytes 0-3: CRC32 (`0x2a790d71`)
- Bytes 4-927: Mostly zeroed data with NVM structure markers
- Bytes 0x31c-0x39c: JSON config fragment with UUID `93bfc3ab-057e-42ac-a595-2ae89e02073e`
- No MAC address, serial number, or SSID present

**Summary:** 43 IP address occurrences, all documentation values (`0.0.0.0`, `127.0.0.1`, `192.0.2.10`). One UUID in EDID file (non-identifying). Zero MACs, serials, or SSIDs.

---

## Build & Packaging

| Item | Status |
| :--- | :--- |
| `pyproject.toml` | Present; `setuptools>=61`, `requests>=2.28,<3` |
| `requirements.txt` | Present; matches pyproject dependencies |
| CI workflow | `.github/workflows/ci.yml`; Python 3.9/3.11/3.12 matrix |
| Shell syntax check | CI runs `sh -n` on payloads |
| Third-party notices | `THIRD_PARTY_NOTICES.md` covers BusyBox GPL, requests Apache-2.0 |

---

## Recommendations

1. **Publish now.** The repo is in good shape; non-blocking items can be addressed post-publication.
2. **Pin CI runner.** Change `ubuntu-latest` to `ubuntu-24.04` for reproducibility.
3. **Document BusyBox provenance.** Add Debian build metadata to THIRD_PARTY_NOTICES.md.
4. **Add sample change note.** Comment in `updatecracked.html` noting placeholder serial format.
5. **Consider `--dry-run` flags.** For NVM/channel-map write tools to reduce user error.

---

## What Was Checked

- [x] Sanitization: MAC/serial/SSID/IP/credential strings
- [x] Build/packaging: pyproject.toml vs requirements.txt source of truth
- [x] CI: Pinned runner, test matrix, shell syntax checks
- [x] Drift: README tables vs research docs consistency
- [x] Provenance: BusyBox, third-party dependencies
- [x] Samples: Change notes vs stock files
- [x] Release mechanics: Version in pyproject.toml (0.3.0)
- [x] Safety surface: Write-capable tools have verify subcommands

---

## Addendum 2026-11-10

New material: `docs/research/18-23`, `tools/probe/`, `tools/install/`,
`evidence/install/`, `evidence/live-inventory/`,
`evidence/usb-autoroot/v8-stateproof/`, and
`payloads/autoscript.stateproof.txt`, and
`payloads/root_boot.opt-block.sh`.

Checks:
- No real IPs, MACs, SSIDs, serials, or workstation paths in the new files.
- `dist/` stays ignored. No binaries are committed.
- The test suite, Python compile step, and shell syntax checks pass.

Verdict: GO.

## Addendum 2026-11-11

New material: `docs/research/24-swdl-telnet-persistence-2026-11-11.md`,
`evidence/tpn256e-variant/`, `assets/banner.svg`, the rebuilt `README.md`, and
the persistence hook detection in `payloads/persist_root.sh`.

Checks:
- The new report and evidence excerpt name a model and firmware but contain no
  serials, MACs, SSIDs, private addresses, or workstation paths.
- The banner and README contain no device data.
- The test suite, Python compile step, and shell syntax checks pass.

Verdict: GO.

## Addendum 2026-11-12

New material: `tools/deep_probe.py`, `tools/bootchain_dump.py`,
`tools/bootchain_inspect.py`, `tools/boot_metadata.py`, `payloads/emmc_backup.sh`,
`docs/research/25`-`29`, `evidence/deep/2026-11-12-8000-bootchain.md`, the
read-only 8000 boot-chain map, and the update-package map.

Checks:
- `deep_probe` and `bootchain_dump` write only under `dist/` on the workstation;
  `bootchain_inspect` and `boot_metadata` read local dumps only.
- The deep probe redacts IPv4/IPv6/MAC/SSID/token/serial-like values and
  preserves documentation ranges.
- The bootchain dumper issues only `dd if=...` reads; it has no `of=` path.
- Raw NVM, pstore, boot slots, partition images, and vendor package components are not committed.
- The changelog is cut to 0.4.0; `pyproject.toml` is 0.4.0 and there is no
  Unreleased section.
- Test coverage is 67 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14

New material: `TIMGPKGVER40` parser support in `tools/firmware/parse_timg.py`
and its tests, the VER40 sections in `docs/research/03` and
`docs/guides/firmware-extraction.md`, the VER40 rows in
`docs/reference/file-formats.md`, and the external `77OLED760/12` (TPN258E)
report under `evidence/tpn258e-77oled760/`.

Checks:
- The parser reads local packages only. It does not execute or decrypt them.
- The TPN258E evidence contains no serials, MACs, SSIDs, IPs, or credentials.
- The TPN236E status line records that the artifact was contributor-supplied
  and that the maintainer reproduced the parser logic and classic-package
  regression only.
- The changelog is cut to 0.4.1; `pyproject.toml` is 0.4.1.
- Test coverage is 71 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (recovery backup)

New material: `STATE.md`, `docs/guides/recovery-gate.md`,
`evidence/deep/2026-11-14-emmc-backup.md`,
`docs/research/30-update-path-2026-11-14.md`, and
`evidence/deep/2026-11-14-update-path.md`.

Checks:
- The backup evidence contains sizes and hashes only. Raw images and the
  bootchain dump stay off the repository.
- The update-path note contains offsets, hashes, function addresses, and no
  vendor payloads or keys. The dump-only package is local under `dist/` and is
  not committed.
- The note names no serial, MAC, SSID, IP, or credential.
- The live-drift section records the persistent-root state without documenting
  the private userspace.
- The changelog is cut to 0.4.2; `pyproject.toml` is 0.4.2.
- Test coverage remains 71 tests; the suite, compile step, and shell syntax
  checks pass.

Verdict: GO.

## Addendum 2026-11-14 (same-byte restore)

New material: the same-byte restore result in
`evidence/deep/2026-11-14-emmc-backup.md`, `STATE.md`,
`docs/guides/recovery-gate.md`, and the recovery tables.

Checks:
- The test wrote only the stock bytes back to `mmcblk0boot0` and
  `mmcblk0boot1`. No modified image was written.
- Both cold boots returned `uid=0`, a fresh uptime, and a new
  `root_boot.ready`. Both boot areas are still `force_ro=1` and hash `eee415…`.
- The docs keep the corrupted-image restore and the boot-area selection/ISP path
  open.
- The changelog is cut to 0.4.3; `pyproject.toml` is 0.4.3.
- Test coverage is 71 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (app-layer update gate)

New material: `docs/research/31-app-update-gate-2026-11-14.md`,
`evidence/deep/2026-11-14-app-update-gate.md`, and the correction in
`docs/research/30`.

Checks:
- The note and evidence contain hashes, offsets, symbol names, and addresses.
  They do not contain private keys, raw vendor payloads, or device identifiers.
- The PEM markers in `libfwup.so` are separate strings; no key block exists.
  The VTBL AES key/pattern values are not published.
- The live `/swdl` header was read only. No package or partition was written.
- The changelog is cut to 0.4.4; `pyproject.toml` is 0.4.4.
- Test coverage is 71 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (eburner flag)

New material: the eburner flag mapping in
`docs/research/31-app-update-gate-2026-11-14.md` and
`evidence/deep/2026-11-14-app-update-gate.md`.

Checks:
- The note and evidence contain hashes, offsets, symbol names, and addresses.
  They do not contain private keys, raw vendor payloads, or device identifiers.
- No flag or partition was written. The `/swdl` header and libraries were read
  only.
- The changelog is cut to 0.4.5; `pyproject.toml` is 0.4.5.
- Test coverage is 71 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (direct staging test)

New material: the direct staging test result in
`docs/research/31-app-update-gate-2026-11-14.md`,
`evidence/deep/2026-11-14-app-update-gate.md`, and `ntkctl --data`.

Checks:
- The test wrote `/swdl`, the p9 flag, and the STBC mode. The p9 flag and STBC
  were restored; the boot areas are unchanged.
- No private keys, raw vendor payloads, or device identifiers are published.
- The vendor package is restored; the p9 hash is the original.
- The changelog is cut to 0.4.6; `pyproject.toml` is 0.4.6.
- Test coverage is 71 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (NDAL V4L2 reset)

New material: `docs/research/32-ndal-v4l2-reset-2026-11-14.md`,
`evidence/deep/2026-11-14-ndal-v4l2-reset.md`, the paused-`appmgr` retry
result in `docs/research/31`, and the updated `STATE.md`.

Checks:
- The note and evidence contain hashes, symbol names, addresses, and offsets.
  They do not contain private keys, raw vendor payloads, or device identifiers.
- The retry staged `/swdl`, set the p9 flag, and set the STBC mode. Cleanup
  restored the vendor `/swdl` package, the p9 `misc`, and the STBC mode; the
  boot areas were not written.
- The vendor package `74d2790a…`, p9 `c32f354f…`, and boot areas `eee415…` are
  restored. The TV and `appmgr` run.
- The `nm` symbol ownership note is a read-only observation of the pulled
  libraries; no vendor bytes are published.
- The changelog is cut to 0.4.7; `pyproject.toml` is 0.4.7.
- Test coverage is 71 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (NDAL V4L2 helper and the full AC-on wrapper)

New material: the corrected NDAL V4L2 control and layout in
`docs/research/32-ndal-v4l2-reset-2026-11-14.md` and
`evidence/deep/2026-11-14-ndal-v4l2-reset.md`, the full-wrapper result in
`docs/research/31-app-update-gate-2026-11-14.md`, and the updated `STATE.md`.

Checks:
- The notes and evidence contain hashes, symbol names, addresses, and offsets.
  They do not contain private keys, raw vendor payloads, or device identifiers.
- The helper and TV libraries stay local; the helper source is not published.
- The test wrote `/swdl` and the p9 flag and set the STBC mode. Cleanup
  restored the vendor `/swdl` package, `autorun_size.txt`,
  `autorun_version.txt`, the p9 `misc`, and the STBC mode; the boot areas were
  not written.
- The vendor package `74d2790a…`, p9 `c32f354f…`, and boot areas `eee415…` are
  restored. The TV and `appmgr` run.
- The full `PLAT_SYS_ResetByHWWDT_PowerOnEventACOn` wrapper consumed
  `/swdl/autorun.upg` but produced no `PKG_SUCCESS` or proof; the eburner
  loader/script remains open.
- The changelog is cut to 0.4.8; `pyproject.toml` is 0.4.8.
- Test coverage is 71 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (TPN236E field report)

New material: `docs/research/33-tpn236e-70pus8108-network-surface-2026-11-14.md`,
its same-day correction, the VER40 confirmation in `docs/research/03`, the
non-JSON success handling in `tools/jointspace_client.py`, the issue forms, and
`ACCESSIBILITY.md`, plus the index rows in `docs/README.md`, `docs/research/12`,
`docs/research/08`, `README.md`, and `evidence/README.md`.

Checks:
- The report records a third-party, read-only probe plus owner-approved
  `VolumeUp` executions. It stays REPORTED and is not presented as
  maintainer-verified.
- The note uses placeholders and contains no serials, MACs, SSIDs, IPs, PINs,
  pairing credentials, private keys, or vendor firmware.
- The note records that `1926` accepted control requests without enforcing the
  advertised pairing. It is a local-LAN finding, not a remote exploit, and it
  does not claim a root entry vector.
- The note does not claim a USB entry vector or an exploit. Hardware tests are
  out of scope until an entry vector exists.
- The issue forms and `ACCESSIBILITY.md` contain no device identifiers,
  credentials, or vendor data.
- The field report is cut to 0.4.9; the correction, issue forms, and
  accessibility work are cut to 0.4.10.
- Docs, the issue forms, and the JointSpace client decoder changed. Test
  coverage is 72 tests; the suite, compile step, and shell syntax checks pass.

Verdict: GO.

## Addendum 2026-11-14 (eburner initramfs and p9 metadata)

New material: the classic eburner initramfs map and p9 metadata layout in
`docs/research/32-ndal-v4l2-reset-2026-11-14.md` and
`evidence/deep/2026-11-14-ndal-v4l2-reset.md`, the USB-path correction in
`docs/research/31-app-update-gate-2026-11-14.md`, and the updated `STATE.md`.

Checks:
- The notes and evidence contain hashes, addresses, symbol names, and a short
  logic excerpt of the initramfs script. They do not contain private keys, raw
  vendor payloads, or device identifiers. The full package and USB image stay
  local.
- The p9 metadata test wrote `UPST` at `0x3600` and `BTFG` at `0x3800`; the
  cleanup restored the pristine p9. The vendor `/swdl`, size/version files, and
  STBC mode were restored; the boot areas were not written. The USB image was
  removed.
- The eburner entry trigger remains open; no boot-area or eMMC writes.
- The changelog is cut to 0.4.11; `pyproject.toml` is 0.4.11.
- Test coverage is 72 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-14 (vendor VER40 USB update and A/B activation)

New material: the vendor update result in
`docs/research/31-app-update-gate-2026-11-14.md`,
`evidence/deep/2026-11-14-ndal-v4l2-reset.md`, `STATE.md`, and
`docs/research/32-ndal-v4l2-reset-2026-11-14.md`.

Checks:
- The notes and evidence contain hashes, addresses, symbol names, and slot
  identifiers. They do not contain private keys, raw vendor payloads, or device
  identifiers. The vendor package stays local.
- The update wrote active slot 0 and boot0 with the genuine vendor package; the
  recovery pair is slot 1/boot1. The old boot-area and p9 backups remain on the
  host. No deliberately corrupted boot area was written.
- Root and persistence survived; the TV runs `002.236.191`.
- The changelog is cut to 0.4.12; `pyproject.toml` is 0.4.12.
- Test coverage is 72 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-15 (TPN236E field note and scope cleanup)

New material: `docs/research/34-tpn236e-43pus7608-2026-11-14.md`, the
`docs/research/03` partition caveat, the `docs/research/33` link and port
differences, `docs/README.md`, `README.md`, `STATE.md`,
`evidence/REDACTION.md`, and the raw-evidence placeholders.

Checks:
- The field note records read-only, owner-authorized probes. It contains no
  serial, MAC, SSID, IP, PIN, pairing credential, or vendor firmware. The
  package artifact hash and table remain unpublished; the static findings are
  marked `REPORTED`, not `VERIFIED`.
- The unrelated custom-userspace project is not named in the public tree or
  the raw evidence. The private userspace is out of scope; raw captures omit
  it.
- The `TPN236E` `p16` target and the `TPN256E` `p19`/`p20` targets are
  recorded as firmware-specific. The no-`quick_debug` and OverlayFS findings
  are marked `TPN236E`-specific. The `:8883` and `:7788` results remain
  unit-specific.
- The derived VER40 offset table is marked derived, not binary-verified. Its
  size closes at `0x250524e4` (`621,094,116` bytes); rows 16-18 correct the
  earlier derivation. SHA-256 and stored-MD5 values are unpublished.
- The changelog is cut to 0.4.13; `pyproject.toml` is 0.4.13.
- Test coverage is 72 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

## Addendum 2026-11-15 (169.001 artifact verification and static follow-up)

New material: `docs/research/35-tpn236e-169001-static-2026-11-15.md`, the
`docs/research/03` verified-offset note, the `docs/research/12` external-report
summary, the `docs/research/25` roadmap refresh, the `docs/research/34`
follow-up links, `docs/guides/faq.md`, `docs/README.md`, `README.md`, and
`STATE.md`.

Checks:
- The note contains public file digests, component MD5s, offsets, symbol names,
  and function offsets. It does not contain vendor firmware, vendor keys,
  serials, MACs, SSIDs, IPs, PINs, pairing credentials, or private keys.
- The `msg_server` finding is a local static pattern with call offsets. It is
  not a remote entry, not an exploit payload, and not a root path without
  `idtv` execution.
- The `169.001` artifact is externally verified; the exact `135.001` artifact
  hash remains unreproduced. The `135.001` reference list is not relabeled as
  the verified `169.001` file.
- The model-support table and FAQ label external reports as REPORTED and keep
  the verified lab separate. They add no universal-support claim.
- The Pages workflow builds from `docs/` and publishes only the generated
  site. `site/` is ignored. It uses no repository secrets and grants only
  `contents: read`, `pages: write`, and `id-token: write`.
- The Discussions welcome and community page contain no serials, credentials,
  pairing data, or vendor firmware. They keep the owner-authorized scope.
- The no-CDP result and the `:1925`/`:1926` behavior are field-unit findings;
  they do not establish a remote entry vector.
- The changelog is cut to 0.4.14; `pyproject.toml` is 0.4.14.
- Test coverage is 72 tests; the suite, compile step, and shell syntax checks
  pass.

Verdict: GO.

*Generated 2026-11-09 from the `philips-titan-tools` repository.*
