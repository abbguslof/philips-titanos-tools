# Glossary

Canonical terms used throughout the repository. If a document uses a different
word for one of these, treat the glossary as authoritative.

## Boot and firmware

**XBoot** — Novatek's early boot firmware on the NT72690. It initialises DDR,
panel, and storage, prints the `uart mode` line, and hands off to ATF. It does
not expose an interactive U-Boot prompt.

**ATF / `a64m`** — ARM Trusted Firmware BL31 on this platform. It brings up the
A55 cores and enters the Linux kernel at EL1.

**eMMC boot partition** — `/dev/mmcblk0boot0` and `/dev/mmcblk0boot1`, two 4 MiB
eMMC boot areas. On the tested unit both contain XBoot.

**Vendor `boot0` / `boot1`** — `/dev/nvt-part-name/boot0` / `boot1`, which map to
user-area partitions `mmcblk0p1` / `p2`. These carry the `UMFG` marker read by
the vendor `run.sh`. They are not the eMMC boot partitions.

**`UMFG`** — the vendor signature string at offset `0x1A0200` in the vendor
`boot0`/`boot1` partitions, followed by a 32-bit `DEBUG_FUNC_LEVEL`.

**`TIMG`** — the outer Novatek firmware container (1.53 GB package).

**`PIMG`** — a component header/payload inside a `TIMG` container.

**`NFSB`** — the secure-filesystem wrapper (4,096-byte header, SHA-256 +
RSA-2048) around the SquashFS images.

**NVM** — the U-Boot-style environment partition `p9`, exported as
`nvm_ubootdat.data`. It is not the bootloader itself.

**SAM** — Service Alignment Mode, the technician menu. It can export/import NVM,
EDID, and channel data.

## Root paths

**Autoroot** — the USB boot-time path that evaluates an `autoscript*.txt` as
root and starts a shell on TCP `:2323`. Ephemeral: remove the stick and cold
boot.

**Persistence hook** — the vendor `customer_env.sh` file on the writable
`apdat` partition. It is sourced early in boot and is used to start a persistent
root listener.

**`apdat`** — the writable ext4 partition `mmcblk0p31`, mounted at
`/mtd_rwarea`; `/mtd_apdat` is a symlink to `/mtd_rwarea/apdat`.

**`quick_debug/menu auto`** — the vendor debug menu in the `mtd_apexe`
application partition. In `auto` mode it waits for the driver marker, finds
`autoscript*.txt` under `/media/sda1`, sleeps 30 seconds, then evaluates the
lines.

**`customer_env.sh`** — the vendor customer-branding environment file sourced by
`run.sh`. The persistence hook appends one line to it.

**`initrc_t`** — the SELinux domain of the vendor init/run scripts. The root
shell and the persistence hook run in this domain.

## USB workflows

**USB autorun stick** — MBR/FAT32 with an **empty label**, so mdev mounts it at
`/media/sda1`. Carries `autoscript.txt`, `autoroot.sh`, and `busybox-armhf`.

**SAM NVM stick** — MBR/FAT32 with the label **`PHILIPS`**, carrying
`SAM/nvm_ubootdat.data`, `SAM/nvm_edid.data`, and/or
`PhilipsChannelMaps/`. Used by the service menu, not by the autorun hook.

Do not use one stick for both workflows without reformatting. The label
determines the mount point, and the two paths expect different mount points.

## Local control

**JointSpace** — the local Philips REST API on ports 1925 (HTTP) and 1926
(HTTPS). Pairing uses Digest auth plus an HMAC-SHA1 PIN handshake.

**`tvtype: consumer`** — the userspace run-mode value that blocks the
engineering JointSpace routes. It is not an IP ACL and is not changed by NVM
`mds_mode`.

**Ambilight `expert` mode** — the JointSpace mode that disables the internal
video override and allows direct per-LED RGB injection.

## Evidence

**VERIFIED** — reproduced on the target hardware or checked against the shipped
artifact.

**TESTED-NEGATIVE** — attempted and failed; the reason is documented.

**INFERRED** — follows from evidence but was not directly observed.

**OPEN** — unresolved.

**Redacted** — identifiers (serial, MAC, SSID, IP, PIN, credentials) replaced
with documentation values or removed.
