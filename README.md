# Philips Titan OS Jailbreak, Root & Reverse-Engineering Toolkit

[![CI](https://github.com/abbguslof/philips-titanos-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/abbguslof/philips-titanos-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-37-brightgreen.svg)](tests/)
[![Target](https://img.shields.io/badge/target-55PUS8000%2F12%20%C2%B7%20TPA256E-orange.svg)](docs/research/01-boot-chain-xboot-atf.md)
[![SoC](https://img.shields.io/badge/SoC-Novatek%20NT72690-red.svg)](docs/research/01-boot-chain-xboot-atf.md)

Research notes, firmware analysis, local-control tooling, and a verified boot-time
**jailbreak/root** path for Philips televisions running **Titan OS** on the Novatek
**NT72690** platform. This is a right-to-repair and reverse-engineering toolkit for
**55PUS8000/12** (`TPA256E` / `TPN256E`): USB autoroot, persistent root, NVM/SAM,
channel maps, JointSpace, Ambilight, firmware extraction, and a documented restore.

**Verified target:** `55PUS8000/12`, chassis `TPA256E` / `TPN256E`, mainboard
`715GD542`, firmware `TPA256E_V056.002.236.191`, Linux 6.1.124 on ARM64 with an
`armv7l` userspace.

> **Scope.** Everything here is for televisions you own. The root path requires
> physical USB access and a cold boot. No remote exploit is claimed. The repo does
> not ship Philips firmware, extracted vendor filesystems, or real device
> identifiers. Read [SECURITY.md](SECURITY.md) before using anything.


| What this is | What this is not |
| :--- | :--- |
| A reproducible research repo for a TV you own: firmware parsing, boot-chain notes, NVM/channel-map tooling, a verified USB root path, and a persistent root hook. | A remote exploit, a cloud bypass for third-party devices, or a vendor firmware mirror. |
| A local-control toolkit: JointSpace, Ambilight `expert` mode, SAM export/import, and the `:2323` root shell. | A custom OS. Product/custom-OS work lives in a separate private project. |
| A physical-access path: USB stick + cold boot, with a documented restore. | A no-risk modification. Read the safety and restore notes first. |

**Start here:** [USB autoroot](docs/guides/usb-autoroot.md) · [persistent root](docs/guides/persistent-root.md) · [firmware acquisition](docs/guides/firmware-acquisition.md) · [documentation index](docs/README.md)

---

## What is verified

| Capability | Status | Evidence |
| :--- | :--- | :--- |
| Interactive `uid=0` shell over TCP `:2323` from a cold boot with a USB stick | **Verified on hardware** | [v4](evidence/usb-autoroot/v4-shell-uid0/), [v7](evidence/usb-autoroot/v7-autoroot-success/) |
| Root shell survives reboot without the USB stick (`customer_env.sh` hook) | **Verified on hardware** | [persistence evidence](evidence/persistence/output.txt) |
| USB autorun stick builder (MBR/FAT32, empty label, SHA-256 verified) | **Verified on hardware** | [`tools/autoroot_usb.py`](tools/autoroot_usb.py) |
| Firmware container parsing (`TIMG` / `PIMG` / `NFSB` / SquashFS LZO) | **Verified statically** | [firmware guide](docs/guides/firmware-extraction.md) |
| U-Boot-style NVM environment read/write with dual CRC32 | **Verified on hardware** | [NVM reference](docs/reference/file-formats.md#uboot-nvm-nvm_ubootdatdata) |
| JointSpace local control (keys, volume, Ambilight, `expert` mode) | **Verified on hardware** | [JointSpace research](docs/research/08-jointspace-api.md) |
| Serial `SERV.U` interactive shell | **Dead on this build** (`ttyS0` TX only; RX never received a byte) | [hardware notes](docs/research/07-hardware-serv-u.md) |
| JointSpace engineering routes (`/6/debug`, `/6/devtools`, ...) | **Dead on this build** (`tvtype: consumer`) | [dead ends](docs/research/12-verified-findings-and-dead-ends.md) |
| Opera/Chromium DevTools on TCP `:7788` | **Open on the LAN; local debug surface** | [webview research](docs/research/13-webview-launcher-ipc.md#chromium-devtools-on-7788) |

The full story, including the paths that failed, is in
[verified findings and dead ends](docs/research/12-verified-findings-and-dead-ends.md).

---

## What root unlocks

Once the USB autoroot path gives you `uid=0`, you can inspect the live system,
dump and verify NVM/EDID/channel maps, parse the firmware container, use
JointSpace/Ambilight locally, and run your own boot-time service. The full list
is in [what root unlocks](docs/guides/what-root-unlocks.md).

| Root capability | Why it matters |
| :--- | :--- |
| Live shell on `:2323` | Inspect mounts, processes, partitions, `ttyS0`, SELinux, and the UI stack. |
| NVM/EDID/channel backups | Recover from a bad service-menu or tuner experiment. |
| Firmware parsing | Understand `TIMG`/`PIMG`/`NFSB`/SquashFS before flashing anything. |
| JointSpace + Ambilight | Local keys, volume, input, per-LED RGB, and live color telemetry. |
| Persistent hook | Start your own userspace service after a cold boot, with a delete-to-restore path. |
| `/swdl` + `apdat` seams | Experiment with local UI/keyboard/config without rootfs writes. |

The public repo stops at research and root. A custom local-first OS layer is a
separate project; this repo is the verified starting point.

---

## Quick start

### 1. Get a root shell from a cold boot

You need a spare USB stick and a physical power cycle. The stick is reformatted.

```bash
git clone https://github.com/abbguslof/philips-titanos-tools.git
cd philips-titanos-tools
sudo ./tools/autoroot_usb.py --device /dev/sdX --host 192.0.2.10
```

Replace `/dev/sdX` with the **whole USB disk** (not a partition) and
`192.0.2.10` with your TV's LAN address. The tool:

- creates an MBR partition table and one FAT32 partition with an **empty label**
  (required: the TV mounts it at `/media/sda1`);
- stages `autoscript.txt`, `autoroot.sh`, and a static armhf busybox;
- verifies SHA-256 and remounts the stick read-only to verify again.

Then:

1. Unplug the TV from AC and wait 10 seconds.
2. Insert the stick into the USB port that enumerates as `sda` on the TV.
3. Plug the TV back in. `quick_debug/menu auto` sleeps **30 seconds** before it
   evaluates the autoscript, so wait at least 45 seconds.
4. Connect with a raw client and run `id`:

```bash
nc <TV_IP> 2323
# or: socat -,raw,echo=0 tcp:<TV_IP>:2323
id
```

Expected: `uid=0(root) ... context=system_u:system_r:initrc_t`.

The detailed walkthrough, failure modes, and restore path are in
[USB autoroot](docs/guides/usb-autoroot.md).

### 2. Make it persistent

From the root shell, install the `customer_env.sh` hook:

```sh
# Serve this repo from your workstation:
#   python3 -m http.server 8000 --bind 0.0.0.0
/tmp/busybox wget -O /tmp/persist_root.sh http://<WORKSTATION_IP>:8000/payloads/persist_root.sh
/bin/sh /tmp/persist_root.sh
```

Remove the USB stick, cold boot, and reconnect. The hook waits for the boot
firewall, starts `telnetd` on `:2323` from `/tmp/persist/busybox`, and writes
`/mtd_rwarea/apdat/root_boot.log`.

See [persistent root](docs/guides/persistent-root.md) and
[restore to stock](docs/guides/restore-to-stock.md).

---

## Documentation map

| Read this | Why |
| :--- | :--- |
| [Documentation index](docs/README.md) | Full index with status labels |
| [Boot chain: XBoot -> ATF -> Linux](docs/research/01-boot-chain-xboot-atf.md) | Why there is no interactive U-Boot |
| [Flash layout and partitions](docs/research/02-flash-layout-and-partitions.md) | The canonical p9/p20/p31/p36 map |
| [Firmware container format](docs/research/03-firmware-container-timg-pimg-nfsb.md) | `TIMG`, `PIMG`, `NFSB`, MD5 vs RSA/SHA-256 |
| [What root unlocks](docs/guides/what-root-unlocks.md) | What you can actually do after the `uid=0` shell |
| [Firmware acquisition](docs/guides/firmware-acquisition.md) | How the package was found, including the historical curl example |
| [Firmware extraction](docs/guides/firmware-extraction.md) | Parse and carve a package without hardcoded offsets |
| [USB autorun hook](docs/research/05-usb-autorun-hook.md) | The exact boot-time eval chain |
| [Persistent root](docs/guides/persistent-root.md) | `customer_env.sh` -> `root_boot.sh` |
| [Hardware `SERV.U`](docs/research/07-hardware-serv-u.md) | Pinout, electrical tests, why RX is dead |
| [JointSpace API](docs/research/08-jointspace-api.md) | Local control, pairing, Ambilight |
| [Service mode (SAM)](docs/research/09-service-mode-sam.md) | NVM/channel/EDID export-import |
| [Network telemetry](docs/research/11-network-telemetry.md) | Ad auctions, ACR, captive-portal pings |
| [Verified findings and dead ends](docs/research/12-verified-findings-and-dead-ends.md) | What is proven, what is dead, what is unknown |
| [Webview, launcher, and native IPC](docs/research/13-webview-launcher-ipc.md) | Chromium/Opera webview (112 UA / 124 CDP), OIPF, BrowserIpcPluginClass, developer sequences, TLS pinning |
| [App framework and startup surface](docs/research/14-app-framework.md) | `nvt.app.ini`, `idtv`/`nbrowser`, local keyboard/offline launcher, `/swdl` overlay |
| [Glossary](docs/reference/glossary.md) | Canonical terms (two different `boot0`s, two USB workflows) |

---

## Repository layout

```text
.
├── docs/
│   ├── research/      verified findings, one topic per file
│   ├── guides/        step-by-step procedures
│   ├── reference/     formats, partition map, glossary
│   └── adr/           architecture decisions
├── payloads/          autoroot.sh, persist_root.sh, busybox, autoscript variants
├── tools/             USB builder, NVM/EDID/channel tools, JointSpace client, firmware tools
├── tests/             37 unit tests (python -m unittest)
├── samples/           small, non-identifying factory samples
├── evidence/          curated, redacted proof runs
└── .github/workflows/ CI
```

---

## Tests

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover tests
```

The suite covers the dual-CRC32 NVM format, CRC-16/MODBUS channel maps, EDID
integrity, JointSpace protocol helpers, USB staging, autoroot staging, and the
persistence installer. Hardware-dependent steps are documented, not faked.

---

## Safety and legal

- **Owned devices only.** Do not use this on a TV you do not own or lack permission to modify.
- **Physical access required.** The root path is a boot-time USB autorun; it is not remote.
- **Warranty and brick risk.** The documented paths avoid flash writes, but you are responsible for your hardware.
- **Restore path.** Pull the USB and cold boot for the ephemeral path; remove the `customer_env.sh` hook for persistence. See [restore to stock](docs/guides/restore-to-stock.md).
- **No vendor firmware in the repo.** The 1.5 GB package is not redistributed. The acquisition guide explains how to obtain the package for your own model and verify it.
- **No real device data.** Serials, MACs, SSIDs, PINs, pairing credentials, and raw captures are redacted or excluded. See [evidence/README.md](evidence/README.md).

This project is independent research and is not affiliated with or endorsed by
Philips, TP Vision, Novatek, or WhaleTV. Trademarks remain the property of their
owners. Original code and documentation are MIT licensed; third-party components
are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

## Keywords

Philips Titan OS jailbreak, Titan OS root, Philips TV root, 55PUS8000/12,
TPA256E, TPN256E, Novatek NT72690, USB autoroot, persistent root, XBoot, ATF,
firmware extraction, TIMG, PIMG, NFSB, SquashFS, U-Boot NVM, dual CRC32, SAM,
Service Alignment Mode, channel maps, CRC-16/MODBUS, JointSpace, Ambilight,
local control, right-to-repair, smart TV reverse engineering, telemetry audit,
debloat.

---

## Contributing and security

- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, tests, redaction rules, PR checklist.
- [SECURITY.md](SECURITY.md) — threat model, disclosure, and what not to report publicly.
- [docs/adr](docs/adr/) — why the repo is structured this way.
