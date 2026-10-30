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

## Generated certificates

`tools/intercept_server.py` can generate a local self-signed certificate for
TLS research. No certificate or private key is committed. Generate your own;
do not reuse a key from another machine.
