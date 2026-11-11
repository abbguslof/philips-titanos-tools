# TPN256E variant autoroot evidence

Status: **external report; redacted excerpt.**

Pedram supplied two USB autoroot logs from a `55PUS8450/12` on firmware
`TPN256E_V056.010.032.001`. They show `uid=0(root)` with the `initrc_t`
context, the USB stick mounted at `/media/sda1`, and `telnetd` listening on
`:2323`.

The logs do not include `root_boot.log` or the `/swdl/telnet/telnetd` wrapper.
They prove the USB autoroot path on this unit. They do not prove the `/swdl`
hook after a USB-less cold boot, so that result stays **REPORTED** in the
[variant note](../../docs/research/24-swdl-telnet-persistence-2026-11-11.md).

The kernel command line also shows `root=/dev/mmcblk0p19`. The verified target
uses `mmcblk0p20`. Treat partition numbers as firmware-specific.
