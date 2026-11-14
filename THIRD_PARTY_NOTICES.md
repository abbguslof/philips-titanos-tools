# Third-Party Notices

This repository's original code and documentation are MIT licensed. The
following third-party material is either included or referenced.

## BusyBox (`payloads/busybox-armhf`)

The static ARM hard-float BusyBox binary is a Debian 1.35.0 build. BusyBox is
licensed under the GNU General Public License, version 2. The corresponding
source is available from Debian:

- https://sources.debian.org/src/busybox/
- https://busybox.net/

If you redistribute the binary, keep the GPL notice and make the corresponding
source available. The payload uses BusyBox only as a userland shell/telnetd on a
device you own; no BusyBox source is modified in this repository.

## Python `requests`

The JointSpace client imports `requests`, licensed under Apache-2.0:

- https://requests.readthedocs.io/
- https://github.com/psf/requests

## Pi-hole / AdGuard blocklist

`tools/pihole/blocklist.txt` is a compiled list of smart-TV telemetry and
advertising domains. It was assembled from public blocklists and live DNS
observations. Before redistributing it further, check the licenses of the
upstream lists you use; this repository does not claim ownership of the domain
data.

## Vendor firmware and device dumps

Philips/TP Vision firmware, extracted SquashFS images, channel-map databases,
NVM dumps, and packet captures are **not** included in this repository. The
`TIMG`/`PIMG`/`NFSB` formats and the NVM/channel-map structures are documented
for interoperability and right-to-repair research. Trademarks and firmware
remain the property of their owners.

## Dropbear SSH

`docs/research/23-dropbear-ssh-2026-11-10.md` documents a static Dropbear
build from <https://github.com/mkj/dropbear>. Dropbear carries its own
permissive licence; see the upstream `LICENSE`. The repository ships no
Dropbear binary. Build output stays in `dist/`, which is ignored.

## Zig

The Dropbear build used Zig 0.17.1 from <https://ziglang.org>. Zig is MIT
licensed. The repository ships no Zig binary.

## unixtract

The firmware extraction guide points to the third-party `unixtract` project at
<https://github.com/theubusu/unixtract> for the vendor decryption step. The
repository does not include or redistribute it. Check the upstream license
before use.

## Generated certificates

`tools/intercept_server.py` can generate a local self-signed certificate for
TLS research. No certificate or private key is committed. Generate your own;
do not reuse a key from another machine.
