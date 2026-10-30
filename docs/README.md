# Documentation Index

Every page carries a status label:

- **VERIFIED** — reproduced on the target TV or checked against the shipped artifact.
- **TESTED-NEGATIVE** — attempted and failed; the reason is documented.
- **INFERRED** — follows from evidence but was not directly observed.
- **OPEN** — not resolved.

## Research

| # | Document | Status | What it answers |
| :-- | :--- | :--- | :--- |
| 01 | [Boot chain: XBoot -> ATF -> Linux](research/01-boot-chain-xboot-atf.md) | VERIFIED | Why there is no interactive U-Boot and what the serial log shows. |
| 02 | [Flash layout and partitions](research/02-flash-layout-and-partitions.md) | VERIFIED | The 40-partition map, p9/p20/p31/p36, and the two different `boot0`s. |
| 03 | [Firmware container: TIMG/PIMG/NFSB](research/03-firmware-container-timg-pimg-nfsb.md) | VERIFIED | Container layout, MD5 vs RSA/SHA-256, `enc=gzip`. |
| 04 | [U-Boot-style NVM format](research/04-uboot-nvm-format.md) | VERIFIED | `nvm_ubootdat.data`, dual CRC32, variables, `mds_mode`. |
| 05 | [USB autorun hook](research/05-usb-autorun-hook.md) | VERIFIED | `S21idtv.sh` -> `run.sh` -> `quick_debug/menu auto` -> `eval`. |
| 06 | [Persistence via `customer_env.sh`](research/06-persistence-customer-env.md) | VERIFIED | The writable boot hook and its ordering constraint. |
| 07 | [Hardware `SERV.U`](research/07-hardware-serv-u.md) | VERIFIED / TESTED-NEGATIVE | Pinout, electrical tests, and why serial RX is dead. |
| 08 | [JointSpace API](research/08-jointspace-api.md) | VERIFIED | Local control, pairing, Ambilight, and the `tvtype: consumer` wall. |
| 09 | [Service mode (SAM)](research/09-service-mode-sam.md) | VERIFIED | Remote sequences, NVM/channel/EDID export-import, dealer options. |
| 10 | [Channel maps](research/10-channel-maps.md) | VERIFIED | `chanLst.bin`, CRC-16/MODBUS, `usr/`. |
| 11 | [Network telemetry](research/11-network-telemetry.md) | VERIFIED | Ad auctions, ACR, captive-portal pings, OTA endpoints. |
| 12 | [Verified findings and dead ends](research/12-verified-findings-and-dead-ends.md) | VERIFIED | One-page truth table and the paths that failed. |
| 13 | [Webview, launcher, and native IPC](research/13-webview-launcher-ipc.md) | VERIFIED / INFERRED | Chromium 112, OIPF, loopback, BrowserIpcPluginClass, developer menu, TLS pinning. |
| 14 | [App framework and startup surface](research/14-app-framework.md) | VERIFIED | `nvt.app.ini`, `idtv`/`nbrowser`, local UI/keyboard assets, `/swdl` overlay. |

## Guides

| Guide | Use it when |
| :--- | :--- |
| [Firmware acquisition](guides/firmware-acquisition.md) | You need the package for your own model, including the historical curl example. |
| [Firmware extraction](guides/firmware-extraction.md) | You have a `.pkg` and want the rootfs/application filesystems. |
| [USB autoroot](guides/usb-autoroot.md) | You want an ephemeral root shell from a cold boot. |
| [Persistent root](guides/persistent-root.md) | You have root and want it to survive a reboot without the stick. |
| [Restore to stock](guides/restore-to-stock.md) | You want to remove the USB path, the persistence hook, or restore NVM. |
| [SAM download from USB](guides/sam-download-from-usb.md) | You are flashing NVM/EDID/channel data through the service menu. |
| [Testing](guides/testing.md) | You are changing the tools or payloads. |

## Reference

| Document | Contents |
| :--- | :--- |
| [Partition map](reference/partition-map.md) | Canonical partition numbers and observed magic. |
| [File formats](reference/file-formats.md) | NVM, EDID, `chanLst.bin`, `TIMG`/`PIMG`/`NFSB`. |
| [Remote sequences](reference/remote-sequences.md) | The 12 six-key sequences, with verification status. |
| [Glossary](reference/glossary.md) | Canonical terms; read this before the research docs. |

## Decisions

- [ADRs](adr/) — why the repo uses two USB workflows, a `customer_env.sh` hook,
  redacted evidence, and a fresh public tree.

The public repo stops at research and root. Product/custom-OS ideas are out of
scope here.

## Evidence and samples

- [Evidence index](../evidence/README.md) — v1-v7 proof runs and UMFG slices.
- [Redaction policy](../evidence/REDACTION.md) — what was removed and why.
- [Samples](../samples/README.md) — small, non-identifying factory data.
