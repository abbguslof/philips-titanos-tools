# Philips Titan OS Toolkit

**Jailbreak, root, and reverse-engineering for Philips TVs running Titan OS on
Novatek NT72690.**

![Philips Titan OS Toolkit](assets/banner.svg)

[Start with USB autoroot](guides/usb-autoroot.md){ .md-button .md-button--primary }
[Check your model](models.md){ .md-button }
[Read the deep roadmap](research/25-deep-jailbreak-roadmap.md){ .md-button }

**Verified on `55PUS8000/12` · 72 tests · release `0.4.14`**

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

- [169.001 artifact verification and static follow-up](research/35-tpn236e-169001-static-2026-11-15.md):
  package hashes, 19/19 stored MD5s, verified offsets, and the 2023 boot chain.
- [43PUS7608/12 field scan](research/34-tpn236e-43pus7608-2026-11-14.md):
  port surface, no CDP, no network entry.
- [70PUS8108/60 network surface](research/33-tpn236e-70pus8108-network-surface-2026-11-14.md):
  JointSpace 6.1 and the unauthenticated `1926` surface.
- [Deep jailbreak roadmap](research/25-deep-jailbreak-roadmap.md):
  Level 3 verified, Level 3.5 next, Level 4 blocked.

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
