# FAQ

Short answers. The linked pages carry the evidence and the limits.

## Is this a remote exploit?

No. The tested `55PUS8000/12` path needs a USB stick and a cold boot. The 2023
`TPN236E` field reports found no network entry vector.

## Does it work on my Philips TV?

Check the [model table](../models.md). The `55PUS8000/12` is
the verified lab. `55PUS8450/12`, `77OLED760/12`, `70PUS8108/60`, and
`43PUS7608/12` are external reports with different limits. Do not copy the 8000
bootchain or kernel carrier to a field unit.

## Will it brick my TV?

Risk exists. The tested unit has a full eMMC backup and a same-byte restore.
Corrupted-image recovery and boot-area selection are still gates. Do not write
a boot image without a tested recovery.

## Does it bypass DRM, Widevine, or the cloud?

No. DRM and secure-world keys are out of scope. This is owner-authorized root
and research on hardware you control.

## Is this a hacking repo?

It is an owner-authorized jailbreak, root, and reverse-engineering repo. It
does not provide a remote exploit, a third-party cloud bypass, or a vendor
firmware mirror. "Hacking" is a search term, not a target.

## Which firmware is tested?

- `55PUS8000/12`: `TPA256E_V056.002.236.191`
- `55PUS8450/12`: `TPN256E_V056.010.032.001`
- `77OLED760/12`: `058.010.032.001`
- `70PUS8108/60`: `TPN236E_V236.004.269.01`
- `43PUS7608/12`: `236.006.169.001`

Firmware-specific details stay firmware-specific. A hook or offset on one build
is not a family fact.

## Why not a custom OS?

This repo stops at research and root. Product and custom-userspace work lives
in a separate private project.

## What is Level 3.5?

Runtime kernel primitives on the owned lab: `kallsyms`, controlled read/write,
verifier inspection, and hardware control. The `ndp_logo` carrier, the runtime
verifier patch, the NFSB mount-path check, and the `ndp_led` backlight are
verified. The full `nvt_dm_setup_nfsb` dm mapping is next. See the
[deep jailbreak roadmap](../research/25-deep-jailbreak-roadmap.md) and the
[carrier page](../research/37-kernel-carrier-level-3-5.md).

## Where do I start?

Read [SECURITY.md](https://github.com/abbguslof/philips-titanos-tools/blob/main/SECURITY.md) first. Then use [USB autoroot](usb-autoroot.md),
[persistent root](persistent-root.md), and [restore to stock](restore-to-stock.md).
For a new model, open a [field report](https://github.com/abbguslof/philips-titanos-tools/issues/new/choose).
