# Supported models

The `55PUS8000/12` is the verified lab. Other models are external reports with
different limits. Do not copy the 8000 bootchain or kernel carrier to a field
unit.

| Model | Chassis | Firmware | Status | Report |
| :--- | :--- | :--- | :--- | :--- |
| **55PUS8000/12** | `TPA256E` / `TPN256E` | `TPA256E_V056.002.236.191` | **VERIFIED (lab)** | [USB root](guides/usb-autoroot.md), [persistence](guides/persistent-root.md), [kernel carrier](research/37-kernel-carrier-level-3-5.md), [backlight](research/39-ndp-led-pwm-backlight-2026-11-20.md), [NFSB verifier](research/40-nfsb-mount-check-2026-11-20.md) |
| 55PUS8450/12 | `TPN256E` | `TPN256E_V056.010.032.001` | **REPORTED** | [USB root evidence](https://github.com/abbguslof/philips-titanos-tools/tree/main/evidence/tpn256e-variant), [portability](research/27-8450-portability.md); `/swdl` persistence is reported, not reproduced |
| 77OLED760/12 | `TPN258E` | `058.010.032.001` | **REPORTED** | [compatibility report](https://github.com/abbguslof/philips-titanos-tools/tree/main/evidence/tpn258e-77oled760); USB root, `/swdl`, SSH; recovery and update untested |
| 70PUS8108/60 | `TPN236E` | `TPN236E_V236.004.269.01` | **REPORTED** | [network surface](research/33-tpn236e-70pus8108-network-surface-2026-11-14.md); no root; `1926` auth gap; `:7788` closed |
| 43PUS7608/12 | `TPN236E` | `236.006.169.001` | **REPORTED / OPEN** | [field scan](research/34-tpn236e-43pus7608-2026-11-14.md), [169.001 artifact](research/35-tpn236e-169001-static-2026-11-15.md); no CDP, no network entry; initial entry open |

## What the status labels mean

- **VERIFIED (lab)**: reproduced on the tested TV or checked against the
  shipped artifact.
- **REPORTED**: tested on hardware by an external contributor, with the unit
  and firmware named. Not independently reproduced by the maintainer.
- **OPEN**: unresolved or not tested.

If your model is missing, open a
[field report](https://github.com/abbguslof/philips-titanos-tools/issues/new/choose)
with the model, chassis, firmware, and what worked or failed. Include whether
the unit is still on the stock firmware and whether you can restore it.
