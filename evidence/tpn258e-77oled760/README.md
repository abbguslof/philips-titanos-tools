# 77OLED760/12 compatibility report

Status: **REPORTED** — externally tested, not maintainer-reproduced.
Model **77OLED760/12**, chassis **TPN258E**, firmware **058.010.032.001**.

Confirmed on this unit:

- USB autoroot provides a root shell.
- The unmodified persistence installer selects `/swdl/telnet/telnetd`;
  root returns after a cold boot with the USB removed.
- Dropbear SSH returns root after a subsequent USB-less cold boot using the
  documented key-only setup. The excerpt shows the session, not the auth
  method.

[Selected redacted output](root-excerpts.txt) records the root identities
and post-boot checks. Recovery, removal and firmware updates were not tested.
