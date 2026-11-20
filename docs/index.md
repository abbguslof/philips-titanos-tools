# Philips Titan OS Toolkit

**Jailbreak, root, and reverse-engineering for Philips TVs running Titan OS on
Novatek NT72690.**

![Philips Titan OS Toolkit](assets/banner.svg)

[Start with USB autoroot](guides/usb-autoroot.md){ .md-button .md-button--primary }
[Check your model](models.md){ .md-button }
[Read the deep roadmap](research/25-deep-jailbreak-roadmap.md){ .md-button }

**Verified on `55PUS8000/12` · 105 tests · release `0.4.17`**

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
| `43PUS7608/12` | `236.006.169.001` | **REPORTED / OPEN** |

If your model is missing, open a
[field report](https://github.com/abbguslof/philips-titanos-tools/issues/new/choose).

## Latest research

- [NFSB mount-path verifier](research/40-nfsb-mount-check-2026-11-20.md):
  the patched verifier accepts a modified loop copy through the runtime check;
  the full dm mapping is open.
- [ndp_led PWM backlight](research/39-ndp-led-pwm-backlight-2026-11-20.md):
  channel 0 duty dimmed and restored through the exported PWM functions.
- [Runtime verifier patch](research/38-runtime-verifier-patch-2026-11-20.md):
  the carrier patches `nfsb_verify` and accepts a modified signature; reboot
  restores the original. The full NFSB dm mapping is open.
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
  Level 3 verified, Level 3.5 carrier/verifier/backlight verified, Level 4
  blocked.

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
