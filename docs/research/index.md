# Documentation Index

Every page carries a status label:

- **VERIFIED** — reproduced on a tested TV or checked against the shipped artifact.
- **REPORTED** — reproduced on hardware by an external contributor, with the unit and firmware named; not independently reproduced by this repo's maintainer.
- **TESTED-NEGATIVE** — attempted and failed; the reason is documented.
- **INFERRED** — follows from evidence but was not directly observed.
- **OPEN** — not resolved.

Current verified state and next gate: [Project status](../project.md). New here? Start
with the [FAQ](../guides/faq.md) and the [model table](../models.md).

Hardware results were produced on the Philips `55PUS8000/12` unless a page names another unit.

The toolkit targets Titan OS on the Novatek NT72690 platform. Other models may differ; reports and PRs are welcome.

## Research

| # | Document | Status | What it answers |
| :-- | :--- | :--- | :--- |
| 01 | [Boot chain: XBoot -> ATF -> Linux](01-boot-chain-xboot-atf.md) | VERIFIED | Why there is no interactive U-Boot and what the serial log shows. |
| 02 | [Flash layout and partitions](02-flash-layout-and-partitions.md) | VERIFIED | The 40-partition map, p9/p11/p20/p31/p36, and the two different `boot0`s. |
| 03 | [Firmware container: TIMG/TIMGPKGVER40/PIMG/NFSB](03-firmware-container-timg-pimg-nfsb.md) | VERIFIED | Classic `TIMG` and `TIMGPKGVER40` layouts, MD5 vs RSA/SHA-256, `enc=gzip`, VER40 vendor encryption. |
| 04 | [U-Boot-style NVM format](04-uboot-nvm-format.md) | VERIFIED | `nvm_ubootdat.data`, dual CRC32, variables, `mds_mode`. |
| 05 | [USB autorun hook](05-usb-autorun-hook.md) | VERIFIED | `S21idtv.sh` -> `run.sh` -> `quick_debug/menu auto` -> `eval`. |
| 06 | [Persistence via `customer_env.sh`](06-persistence-customer-env.md) | VERIFIED | The writable boot hook and its ordering constraint. |
| 07 | [Hardware `SERV.U`](07-hardware-serv-u.md) | VERIFIED / TESTED-NEGATIVE | Pinout, electrical tests, and why serial RX is dead. |
| 08 | [JointSpace API](08-jointspace-api.md) | VERIFIED | Local control, pairing, Ambilight, and the `tvtype: consumer` wall. |
| 09 | [Service mode (SAM)](09-service-mode-sam.md) | VERIFIED | Remote sequences, NVM/channel/EDID export-import, dealer options. |
| 10 | [Channel maps](10-channel-maps.md) | VERIFIED | `chanLst.bin`, CRC-16/MODBUS, `usr/`. |
| 11 | [Network telemetry](11-network-telemetry.md) | VERIFIED | Ad auctions, ACR, captive-portal pings, OTA endpoints. |
| 12 | [Verified findings and dead ends](12-verified-findings-and-dead-ends.md) | VERIFIED | One-page truth table and the paths that failed. |
| 13 | [Webview, launcher, and native IPC](13-webview-launcher-ipc.md) | VERIFIED / INFERRED | Chromium/Opera webview (112 UA / 124 CDP), OIPF, loopback, BrowserIpcPluginClass, developer menu, TLS pinning. |
| 14 | [App framework and startup surface](14-app-framework.md) | VERIFIED | `nvt.app.ini`, `idtv`/`nbrowser`, local UI/keyboard assets, `/swdl` overlay. |
| 15 | [SELinux runtime control](15-selinux-runtime-control.md) | VERIFIED / WORKING | Whole-policy `dd` load, v33 all-types-permissive policy at boot, working `mounton`, Settings/menus verified after cold boot; `setenforce` remains `EINVAL`. |
| 16 | [Kernel, module, and hardware control surfaces](16-kernel-and-hardware-control.md) | VERIFIED / PERSISTENT SELOFF | Vendor `.ko` files, unsigned module load, verified kernel code execution and `selinux_state` read/write, persistent seloff boot payload with kill switch, plus hardware nodes. |
| 17 | [Runtime NFSB bypass: raw SquashFS mount](17-runtime-nfsb-squashfs.md) | VERIFIED | Direct read-only SquashFS mount at offset `0x1000`; the verifier and dm-verity guard the `nfsb` mount; flash/boot remain blocked. |
| 18 | [Live inventory](18-live-inventory-2026-11-09.md) | VERIFIED / OPEN | Boot, SELinux, mounts, device nodes, TEE, dm-verity, and tooling on the live unit. |
| 19 | [Control surfaces](19-phase-b-control-surfaces-2026-11-09.md) | VERIFIED / OPEN | Measured `ntkmem` ABI, V4L2 HDMI, GPIO lines, and the per-node probe order. |
| 20 | [USB stateproof](20-usb-stateproof-2026-11-10.md) | VERIFIED / OPEN | A non-resetting autoscript writes boot state to the stick. |
| 21 | [Install prefix](21-install-prefix-2026-11-10.md) | VERIFIED | A static tool runs from `/mtd_rwarea/apdat/opt`. |
| 22 | [Install persistence](22-opt-prefix-persistence-2026-11-10.md) | VERIFIED | The prefix and `PATH` survive a cold boot with the USB removed. |
| 23 | [Dropbear SSH](23-dropbear-ssh-2026-11-10.md) | VERIFIED | Static key-only SSH on `:2222` survives a cold boot. |
| 24 | [Firmware variant: `/swdl/telnet/telnetd`](24-swdl-telnet-persistence-2026-11-11.md) | REPORTED | A later `TPN256E` firmware dropped `customer_env.sh`; the vendor `/swdl` seam restores USB-less persistence. |
| 25 | [Deep jailbreak roadmap](25-deep-jailbreak-roadmap.md) | PLAN / STARTED | The 8000 lab ladder, Level 3.5 vs Level 4, field-unit rules, and the recovery gate. |
| 26 | [Recovery engineering](26-recovery-engineering.md) | PLAN | Boot-area, eMMC ISP/JTAG, UART RX, restore test, and stop conditions. |
| 27 | [55PUS8450/12 portability](27-8450-portability.md) | REPORTED / PLAN | Field-unit differences, read-only comparison, and `/swdl` persistence proof. |
| 28 | [Boot image map](28-boot-image-map.md) | VERIFIED (read-only) | Protected A/B secure slots, plain `p21` `kerupm` upgrade kernel, `p1/p2` UMFG slots, and the `p9` slot map. |
| 29 | [Update package map](29-update-package-map.md) | VERIFIED (local package) | Package-to-live component match; signed secure components; plain `kerupm`; RAM update environment and the MD5-only burner. |
| 30 | [Update path: package map, burner checks, and the dump-only test](30-update-path-2026-11-14.md) | VERIFIED / INFERRED | Component map, MD5-only burner checks, live slot matches, and the prepared dump-only test package. |
| 31 | [App-layer update gate: `/swdl` trigger and RSA verification](31-app-update-gate-2026-11-14.md) | VERIFIED (hardware) / OPEN | Genuine VER40 USB update programmed active slot 0 and activated on AC-on (`002.236.191`); RSA remains the modified-package barrier; recovery slot 1/boot1. |
| 32 | [NDAL V4L2 reset path and the eburner retries](32-ndal-v4l2-reset-2026-11-14.md) | VERIFIED (static) / TESTED-NEGATIVE / OPEN | The exact control (`0x0f170f1f`), `/dev/video24`, the classic eburner USB-image initramfs, the p9 metadata layout, and the open eburner entry trigger. |
| 33 | [70PUS8108/60 (TPN236E) network surface](33-tpn236e-70pus8108-network-surface-2026-11-14.md) | REPORTED | Read-only port and JointSpace 6.1 probes on a 2023 TPN236E unit: no root entry vector, an unauthenticated `1926` control surface, the corrected POST `503`, and `8883`/`:7788` closed on default boot. |
| 34 | [43PUS7608/12 (TPN236E) field scan and static notes](34-tpn236e-43pus7608-2026-11-14.md) | REPORTED / INFERRED / OPEN (135.001 hash) | Second TPN236E field scan (`236.006.169.001`): eight open ports, expired MQTT cert, `:7788` closed on default boot, no network entry; external `169.001` artifact verification; exact `135.001` hash still open. The physical entry is live-verified in note 42. |
| 35 | [43PUS7608/12 169.001 artifact and static follow-up](35-tpn236e-169001-static-2026-11-15.md) | REPORTED (external) | ZIP/autorun SHA-256, 19/19 stored MD5, verified PIMG offsets; `stbc_emmc` 8051, `xboot` second layer, no `eburner`; no CDP on default boot; `msg_server` local root queue. |
| 36 | [43PUS7608/12 169.001 corrections and local access findings](36-tpn236e-169001-corrections-2026-11-16.md) | REPORTED (external) | Issue #8 corrections: `msg_server`/`cmd_daemon` labels, `initrc_t`, active `cmd_daemon`; serial root candidate; USB-gated CDP; SELinux groups; `core_helper` refuted. Physical/local only. |
| 37 | [Level 3.5: reusable kernel carrier](37-kernel-carrier-level-3-5.md) | VERIFIED (hardware) | KCFI-aware merge into the vendor `ndp_logo.ko`, a sysfs mailbox, runtime symbol resolution, 64-bit read/write/call, live load and reads, rollback and reboot. Direct verifier patch, mount-path check, full dm mapping, and dm-verity data path verified. |
| 38 | [2026-11-20 runtime verifier patch](38-runtime-verifier-patch-2026-11-20.md) | VERIFIED (hardware) | Direct `nfsb_verify` patch: pristine header accepted, modified signature rejected, patched function accepts it; reboot restores the original. Full NFSB dm mapping verified in 43 and the dm-verity data path in 44. |
| 39 | [2026-11-20 ndp_led PWM backlight](39-ndp-led-pwm-backlight-2026-11-20.md) | VERIFIED (hardware) | Exported `KER_LED_PWM_HWFR_Get_Duty`/`Set_Duty`: channel 0 duty 20000/offset 105, dim to 10000, restore; reboot returns the default. |
| 40 | [2026-11-20 NFSB mount-path verifier](40-nfsb-mount-check-2026-11-20.md) | VERIFIED (hardware) | `nvt_dm_check_nfsb` rejects a modified loop copy unpatched and accepts it after the `nfsb_verify` patch; the full dm mapping is verified in 43. |
| 41 | [55PUS8108/12 FZ1A on 169.001](41-tpn236e-55pus8108-2026-11-21.md) | REPORTED (hardware), VERIFIED (offline) | One privileged boot record, USB diagnostics, browser playback, media stack, and source archive inventory. |
| 42 | [43PUS7608/12 USB flag -> CDP -> RPC injection -> root](42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md) | REPORTED (live) / OPEN (55PUS8108 probe) | The USB flag opens CDP; the launcher RPC bridge injects a shell command as `idtv`; `customer_env.sh` grants root. A stick-free reboot also reproduced root and both listeners. A second static sink and the adID telemetry leak are recorded. |
| 43 | [Full NFSB dm mapping](43-nfsb-dm-mapping-2026-11-22.md) | VERIFIED (hardware) | `nvt_dm_setup_linear` and `nvt_dm_setup_nfsb` build the `linear` and `verity` targets; a read-only loop copy mounts the stock SquashFS. The header field map and target params are recorded. The dm-verity data path is verified in 44. |
| 44 | [2026-11-22 dm-verity data path](44-nfsb-verity-data-path-2026-11-22.md) | VERIFIED (hardware) | A modified data block reads through the verity device after the tree is recomputed and the header root digest is replaced; the stock tree/digest still returns EIO. A custom NFSB image is mounted in 45. |
| 45 | [2026-11-22 custom NFSB mount](45-custom-nfsb-mount-2026-11-22.md) | VERIFIED (hardware) / one-block edge explained | A host-built SquashFS + NFSB header/tree mounts read-only through `nvt_dm_setup_linear` + `nvt_dm_setup_nfsb`. One data block has zero hash levels; the root is `H(salt\|\|data)` and there is no tree block. |

## Guides

| Guide | Use it when |
| :--- | :--- |
| [FAQ](../guides/faq.md) | You want a short answer before reading the deep pages. |
| [What root unlocks](../guides/what-root-unlocks.md) | You want the concrete capabilities after the `uid=0` shell. |
| [Firmware acquisition](../guides/firmware-acquisition.md) | You need the package for your own model, including the historical curl example. |
| [Firmware extraction](../guides/firmware-extraction.md) | You have a `.pkg` and want the rootfs/application filesystems. |
| [USB autoroot](../guides/usb-autoroot.md) | You want an ephemeral root shell from a cold boot. |
| [Persistent root](../guides/persistent-root.md) | You have root and want it to survive a reboot without the stick. |
| [Recovery gate](../guides/recovery-gate.md) | You are about to write a boot area or the update environment. |
| [Restore to stock](../guides/restore-to-stock.md) | You want to remove the USB path, the persistence hook, or restore NVM. |
| [SAM download from USB](../guides/sam-download-from-usb.md) | You are flashing NVM/EDID/channel data through the service menu. |
| [Testing](../guides/testing.md) | You are changing the tools or payloads. |

## Reference

| Document | Contents |
| :--- | :--- |
| [Partition map](../reference/partition-map.md) | Canonical partition numbers and observed magic. |
| [File formats](../reference/file-formats.md) | NVM, EDID, `chanLst.bin`, `TIMG`/`PIMG`/`NFSB`. |
| [Remote sequences](../reference/remote-sequences.md) | The 12 six-key sequences, with verification status. |
| [Glossary](../reference/glossary.md) | Canonical terms; read this before the research docs. |

## Decisions

- [ADRs](../adr/index.md) — why the repo uses two USB workflows, vendor boot hooks,
  redacted evidence, and a fresh public tree.

The public repo stops at research and root. Product/custom-OS ideas are out of
scope here.

## Evidence and samples

- [Evidence index](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/README.md) — v1-v7 proof runs and UMFG slices.
- [Redaction policy](https://github.com/abbguslof/philips-titanos-tools/blob/main/evidence/REDACTION.md) — what was removed and why.
- [Samples](https://github.com/abbguslof/philips-titanos-tools/blob/main/samples/README.md) — small, non-identifying factory data.
