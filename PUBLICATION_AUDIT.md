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

*Generated 2026-11-09 from the `philips-titan-tools` repository.*
