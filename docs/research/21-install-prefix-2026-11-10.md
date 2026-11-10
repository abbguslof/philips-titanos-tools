# Install prefix: durable static tools on apdat

Status: **VERIFIED** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-10.

Steps 1-2 only: create the prefix and prove a static binary runs from
`/mtd_rwarea/apdat`. No boot hook and no SSH were installed. The rootfs and
all boot/partition data are untouched.

## Why this shape

- `/` is read-only SquashFS (`evidence/usb-autoroot/v8-stateproof/proof.txt:7`).
- `/mtd_rwarea/apdat` is rw ext4 (`proof.txt:29`), so it is the durable prefix.
- Userspace is 32-bit ARM EABI5 (armhf); the kernel is aarch64. A **static**
  binary avoids the missing libc/loader path. No compiler exists on the TV.

## Tool

`tools/install/lsblk.c:1-8` is a freestanding static armhf `lsblk`-lite that
reads `/proc/partitions`. It uses no libc, no dynamic loader, and no division
instruction.

Build: `tools/install/README.md` (clang + ld.lld, `-static -no-pie`).

Binary sha256:
`af07f0218ecbabb45913abdfe8ccc9beb5b16d8d4223e998b9ba977386d87f2e`
(`evidence/install/proof-1.txt`, hash line).

## Install and result

On-device (`evidence/install/proof-1.txt`):

| Step | Result |
| :--- | :--- |
| `mkdir -p /mtd_rwarea/apdat/opt/{bin,etc,lib,var}` | ok |
| wget static `lsblk` to `opt/bin/lsblk` | ok |
| `chmod 0755` | ok |
| on-device `sha256sum` | matches workstation build |
| direct run `opt/bin/lsblk` | prints 74 block rows (all of `/proc/partitions`) |
| `PATH=/mtd_rwarea/apdat/opt/bin:$PATH lsblk` | resolves and runs |
| `df` before/after | unchanged at 315.6 M free / 81% used |

So a self-contained binary can live on the writable partition and be reached
through `PATH`. The same prefix is where Dropbear and future tools go.

## Not done (deliberately)

- No `customer_env.sh` edit; nothing starts at boot yet.
- No SSH server.
- No cold-boot persistence test for `PATH`.

## Next

1. Add `opt/boot.sh` that waits for `/tmp/ntkdriver_completed` + 5 s, exports
   `PATH=/mtd_rwarea/apdat/opt/bin:$PATH`, and is launched by one appended line
   in `customer_env.sh` (ordering trap: `06-persistence-customer-env.md:24-39`).
2. Cold boot with the USB removed; confirm `lsblk` resolves and the unit
   stays up.
3. Then Dropbear on a non-default port, key-only, with host key and
   `authorized_keys` persisted under `opt/etc`, and one firewall ACCEPT rule
   inserted after `iptables_conf.sh`.

## Safety

Writes were confined to `/mtd_rwarea/apdat/opt`. No flash, boot, or partition
writes. `customer_env.sh` is unchanged; the USB autoroot stick remains the
recovery path.
