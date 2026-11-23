# Philips Titan OS Toolkit

**Jailbreak, root, and reverse-engineering for Philips TVs running Titan OS on
Novatek NT72690.**

![Philips Titan OS Toolkit](assets/banner.svg)

[Start with USB autoroot](guides/usb-autoroot.md){ .md-button .md-button--primary }
[Check your model](models.md){ .md-button }
[Read the deep roadmap](research/25-deep-jailbreak-roadmap.md){ .md-button }

**Verified on `55PUS8000/12` · 118 tests · release `0.4.25`**

!!! warning "Scope"
    This is an owner-authorized repository for TVs you own. The tested root
    path needs a USB stick and a cold boot. It is not a remote exploit, a
    cloud bypass, a firmware mirror, or a custom OS. Read
    [SECURITY.md](https://github.com/abbguslof/philips-titanos-tools/blob/main/SECURITY.md) before you start.

## Start by goal

| I want to... | Go to |
| :--- | :--- |
| Get a root shell from a cold boot | [USB autoroot](guides/usb-autoroot.md) |
| Keep root after a reboot | [Persistent root](guides/persistent-root.md) |
| Remove root and return to stock | [Restore to stock](guides/restore-to-stock.md) |
| Check whether my model is supported | [Supported models](models.md) |
| Understand the boot chain | [Boot chain: XBoot to ATF to Linux](research/01-boot-chain-xboot-atf.md) |
| Read the deepest jailbreak plan | [Deep jailbreak roadmap](research/25-deep-jailbreak-roadmap.md) |
| See what is proven and what is dead | [Verified findings and dead ends](research/12-verified-findings-and-dead-ends.md) |

## Supported models

The `55PUS8000/12` is the verified lab. Other models are external reports with
different limits. The full table is in [Supported models](models.md).

| Model | Firmware | Status |
| :--- | :--- | :--- |
| `55PUS8000/12` | `TPA256E_V056.002.236.191` | **VERIFIED (lab)** |
| `55PUS8450/12` | `TPN256E_V056.010.032.001` | **REPORTED** |
| `77OLED760/12` | `058.010.032.001` | **REPORTED** |
| `70PUS8108/60` | `TPN236E_V236.004.269.01` | **REPORTED** |
| `43PUS7608/12` | `236.006.169.001` | **REPORTED (root)** |
| [`55PUS8108/12`](research/41-tpn236e-55pus8108-2026-11-21.md) | `236.006.169.001` | **REPORTED** |
| `50PUS8909/12` | `TPN248E_V248.010.000.121` | **REPORTED / OPEN** |

If your model is missing, open a
[field report](https://github.com/abbguslof/philips-titanos-tools/issues/new/choose).

## Latest research

- [A/B switch failure](research/48-ab-switch-failure-2026-11-22.md):
  slot 0 fails `lnikauth`; the old slot 1/boot1 is the licensed pair; the
  recovery is p9 DBFG 2 and `EXT_CSD 0x50`.
- [Titan OS control field reports](research/47-titanos-control-field-reports-2026-11-22.md):
  external JointSpace 6.1, Titan OS MQTT, DIAL, Wake-on-LAN, Ambilight Off node
  300, and JointSpace stability reports. No root conclusion.
- [Level 4 boot-chain map](research/46-level4-boot-chain-map-2026-11-22.md):
  the A/B pair, static VTBL/NVHC/U-Boot slots, encrypted XBoot, component
  trailers, and the eMMC boot-part switch. The A/B switch to slot 0 is
  TESTED-NEGATIVE.
- [Custom NFSB image mount](research/45-custom-nfsb-mount-2026-11-22.md):
  a host-built SquashFS + NFSB header/tree mounts read-only through the runtime
  setup. The one-block case is explained (dm-verity zero hash levels).
- [dm-verity data path](research/44-nfsb-verity-data-path-2026-11-22.md):
  a modified data block reads through the verity device after the tree is
  recomputed and the header root digest is replaced; the stock tree/digest still
  returns EIO. The next target is a custom mountable NFSB image.
- [Full NFSB dm mapping](research/43-nfsb-dm-mapping-2026-11-22.md):
  `nvt_dm_setup_linear` and `nvt_dm_setup_nfsb` build the `linear` and `verity`
  targets; a read-only loop copy mounts the stock SquashFS.
- [43PUS7608/12 RPC-injection root](research/42-tpn236e-43pus7608-rpc-injection-root-2026-11-21.md):
  a USB flag opens CDP, the launcher RPC bridge injects a shell command as
  `idtv`, and the boot hook grants root. A later boot with the stick removed
  reproduced root and both listeners. External and live-verified.
- [55PUS8108/12 field report](research/41-tpn236e-55pus8108-2026-11-21.md):
  repeatable fixed-command access, an owner-built ARM probe, browser playback,
  USB diagnostics and measured eMMC backup coverage.
- [NFSB mount-path verifier](research/40-nfsb-mount-check-2026-11-20.md):
  the patched verifier accepts a modified loop copy through the runtime check;
  the full dm mapping is verified in
  [43](research/43-nfsb-dm-mapping-2026-11-22.md).
- [ndp_led PWM backlight](research/39-ndp-led-pwm-backlight-2026-11-20.md):
  channel 0 duty dimmed and restored through the exported PWM functions.
- [Runtime verifier patch](research/38-runtime-verifier-patch-2026-11-20.md):
  the carrier patches `nfsb_verify` and accepts a modified signature; reboot
  restores the original. The full NFSB dm mapping is verified in
  [43](research/43-nfsb-dm-mapping-2026-11-22.md).
- [Level 3.5 reusable kernel carrier](research/37-kernel-carrier-level-3-5.md):
  KCFI-aware build/control tooling for runtime kernel read/write and calls,
  verified on the lab, including the direct verifier patch.
- [169.001 artifact verification and static follow-up](research/35-tpn236e-169001-static-2026-11-15.md):
  package hashes, 19/19 stored MD5s, verified offsets, and the 2023 boot chain.
- [43PUS7608/12 field scan](research/34-tpn236e-43pus7608-2026-11-14.md):
  port surface, no default CDP, no network entry.
- [169.001 corrections](research/36-tpn236e-169001-corrections-2026-11-16.md):
  `cmd_daemon` active, `msg_server` runtime domain, serial/USB-gated physical paths.
- [70PUS8108/60 network surface](research/33-tpn236e-70pus8108-network-surface-2026-11-14.md):
  JointSpace 6.1 and the unauthenticated `1926` surface.
- [Deep jailbreak roadmap](research/25-deep-jailbreak-roadmap.md):
  Level 3 verified, Level 3.5 complete, Level 4 boot chain mapped; the A/B
  switch to slot 0 is TESTED-NEGATIVE; the old slot 1 is licensed; the recovery
  is the p9/`EXT_CSD`.

## Documentation

The [documentation index](research/index.md) lists all research notes, guides, and
reference pages. Use the search box for exact model numbers, firmware strings,
function names, and error text.

## Project

The toolkit is MIT-licensed. The [project status](project.md),
[changelog](https://github.com/abbguslof/philips-titanos-tools/blob/main/CHANGELOG.md), and [security policy](https://github.com/abbguslof/philips-titanos-tools/blob/main/SECURITY.md) are kept in the
repository. Contributions, questions, and field reports are welcome in
[GitHub Discussions](https://github.com/abbguslof/philips-titanos-tools/discussions)
and on [GitHub](https://github.com/abbguslof/philips-titanos-tools).
