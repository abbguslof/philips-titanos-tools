# Documentation Index

Every page carries a status label:

- **VERIFIED** — reproduced on a tested TV or checked against the shipped artifact.
- **REPORTED** — reproduced on hardware by an external contributor, with the unit and firmware named; not independently reproduced by this repo's maintainer.
- **TESTED-NEGATIVE** — attempted and failed; the reason is documented.
- **INFERRED** — follows from evidence but was not directly observed.
- **OPEN** — not resolved.

Current verified state and next gate: [STATE.md](../STATE.md).

Hardware results were produced on the Philips `55PUS8000/12` unless a page names another unit.

The toolkit targets Titan OS on the Novatek NT72690 platform. Other models may differ; reports and PRs are welcome.

## Research

| # | Document | Status | What it answers |
| :-- | :--- | :--- | :--- |
| 01 | [Boot chain: XBoot -> ATF -> Linux](research/01-boot-chain-xboot-atf.md) | VERIFIED | Why there is no interactive U-Boot and what the serial log shows. |
| 02 | [Flash layout and partitions](research/02-flash-layout-and-partitions.md) | VERIFIED | The 40-partition map, p9/p11/p20/p31/p36, and the two different `boot0`s. |
| 03 | [Firmware container: TIMG/TIMGPKGVER40/PIMG/NFSB](research/03-firmware-container-timg-pimg-nfsb.md) | VERIFIED | Classic `TIMG` and `TIMGPKGVER40` layouts, MD5 vs RSA/SHA-256, `enc=gzip`, VER40 vendor encryption. |
| 04 | [U-Boot-style NVM format](research/04-uboot-nvm-format.md) | VERIFIED | `nvm_ubootdat.data`, dual CRC32, variables, `mds_mode`. |
| 05 | [USB autorun hook](research/05-usb-autorun-hook.md) | VERIFIED | `S21idtv.sh` -> `run.sh` -> `quick_debug/menu auto` -> `eval`. |
| 06 | [Persistence via `customer_env.sh`](research/06-persistence-customer-env.md) | VERIFIED | The writable boot hook and its ordering constraint. |
| 07 | [Hardware `SERV.U`](research/07-hardware-serv-u.md) | VERIFIED / TESTED-NEGATIVE | Pinout, electrical tests, and why serial RX is dead. |
| 08 | [JointSpace API](research/08-jointspace-api.md) | VERIFIED | Local control, pairing, Ambilight, and the `tvtype: consumer` wall. |
| 09 | [Service mode (SAM)](research/09-service-mode-sam.md) | VERIFIED | Remote sequences, NVM/channel/EDID export-import, dealer options. |
| 10 | [Channel maps](research/10-channel-maps.md) | VERIFIED | `chanLst.bin`, CRC-16/MODBUS, `usr/`. |
| 11 | [Network telemetry](research/11-network-telemetry.md) | VERIFIED | Ad auctions, ACR, captive-portal pings, OTA endpoints. |
| 12 | [Verified findings and dead ends](research/12-verified-findings-and-dead-ends.md) | VERIFIED | One-page truth table and the paths that failed. |
| 13 | [Webview, launcher, and native IPC](research/13-webview-launcher-ipc.md) | VERIFIED / INFERRED | Chromium/Opera webview (112 UA / 124 CDP), OIPF, loopback, BrowserIpcPluginClass, developer menu, TLS pinning. |
| 14 | [App framework and startup surface](research/14-app-framework.md) | VERIFIED | `nvt.app.ini`, `idtv`/`nbrowser`, local UI/keyboard assets, `/swdl` overlay. |
| 15 | [SELinux runtime control](research/15-selinux-runtime-control.md) | VERIFIED / WORKING | Whole-policy `dd` load, v33 all-types-permissive policy at boot, working `mounton`, Settings/menus verified after cold boot; `setenforce` remains `EINVAL`. |
| 16 | [Kernel, module, and hardware control surfaces](research/16-kernel-and-hardware-control.md) | VERIFIED / PERSISTENT SELOFF | Vendor `.ko` files, unsigned module load, verified kernel code execution and `selinux_state` read/write, persistent seloff boot payload with kill switch, plus hardware nodes. |
| 17 | [Runtime NFSB bypass: raw SquashFS mount](research/17-runtime-nfsb-squashfs.md) | VERIFIED | Direct read-only SquashFS mount at offset `0x1000`; the verifier and dm-verity guard the `nfsb` mount; flash/boot remain blocked. |
| 18 | [Live inventory](research/18-live-inventory-2026-11-09.md) | VERIFIED / OPEN | Boot, SELinux, mounts, device nodes, TEE, dm-verity, and tooling on the live unit. |
| 19 | [Control surfaces](research/19-phase-b-control-surfaces-2026-11-09.md) | VERIFIED / OPEN | Measured `ntkmem` ABI, V4L2 HDMI, GPIO lines, and the per-node probe order. |
| 20 | [USB stateproof](research/20-usb-stateproof-2026-11-10.md) | VERIFIED / OPEN | A non-resetting autoscript writes boot state to the stick. |
| 21 | [Install prefix](research/21-install-prefix-2026-11-10.md) | VERIFIED | A static tool runs from `/mtd_rwarea/apdat/opt`. |
| 22 | [Install persistence](research/22-opt-prefix-persistence-2026-11-10.md) | VERIFIED | The prefix and `PATH` survive a cold boot with the USB removed. |
| 23 | [Dropbear SSH](research/23-dropbear-ssh-2026-11-10.md) | VERIFIED | Static key-only SSH on `:2222` survives a cold boot. |
| 24 | [Firmware variant: `/swdl/telnet/telnetd`](research/24-swdl-telnet-persistence-2026-11-11.md) | REPORTED | A later `TPN256E` firmware dropped `customer_env.sh`; the vendor `/swdl` seam restores USB-less persistence. |
| 25 | [Deep jailbreak roadmap](research/25-deep-jailbreak-roadmap.md) | PLAN / STARTED | The 8000 lab ladder, Level 3.5 vs Level 4, field-unit rules, and the recovery gate. |
| 26 | [Recovery engineering](research/26-recovery-engineering.md) | PLAN | Boot-area, eMMC ISP/JTAG, UART RX, restore test, and stop conditions. |
| 27 | [55PUS8450/12 portability](research/27-8450-portability.md) | REPORTED / PLAN | Field-unit differences, read-only comparison, and `/swdl` persistence proof. |
| 28 | [Boot image map](research/28-boot-image-map.md) | VERIFIED (read-only) | Protected A/B secure slots, plain `p21` `kerupm` upgrade kernel, `p1/p2` UMFG slots, and the `p9` slot map. |
| 29 | [Update package map](research/29-update-package-map.md) | VERIFIED (local package) | Package-to-live component match; signed secure components; plain `kerupm`; RAM update environment and the MD5-only burner. |
| 30 | [Update path: package map, burner checks, and the dump-only test](research/30-update-path-2026-11-14.md) | VERIFIED / INFERRED | Component map, MD5-only burner checks, live slot matches, and the prepared dump-only test package. |
| 31 | [App-layer update gate: `/swdl` trigger and RSA verification](research/31-app-update-gate-2026-11-14.md) | VERIFIED / OPEN | USB trigger, `/swdl/autorun.upg` is VER40, RSA public-key verifier, no private key, direct staging bypass plan. |

## Guides

| Guide | Use it when |
| :--- | :--- |
| [What root unlocks](guides/what-root-unlocks.md) | You want the concrete capabilities after the `uid=0` shell. |
| [Firmware acquisition](guides/firmware-acquisition.md) | You need the package for your own model, including the historical curl example. |
| [Firmware extraction](guides/firmware-extraction.md) | You have a `.pkg` and want the rootfs/application filesystems. |
| [USB autoroot](guides/usb-autoroot.md) | You want an ephemeral root shell from a cold boot. |
| [Persistent root](guides/persistent-root.md) | You have root and want it to survive a reboot without the stick. |
| [Recovery gate](guides/recovery-gate.md) | You are about to write a boot area or the update environment. |
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

- [ADRs](adr/) — why the repo uses two USB workflows, vendor boot hooks,
  redacted evidence, and a fresh public tree.

The public repo stops at research and root. Product/custom-OS ideas are out of
scope here.

## Evidence and samples

- [Evidence index](../evidence/README.md) — v1-v7 proof runs and UMFG slices.
- [Redaction policy](../evidence/REDACTION.md) — what was removed and why.
- [Samples](../samples/README.md) — small, non-identifying factory data.
