# Install prefix: USB-less cold-boot persistence

Status: **VERIFIED** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-10.

The `/mtd_rwarea/apdat/opt` prefix survives a cold boot with the USB removed,
and the persistent login shell resolves tools from it.

## Change (one line)

`/mtd_rwarea/apdat/root_boot.sh:12`:

```sh
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/mtd_rwarea/apdat/opt/bin
```

Backup: `root_boot.sh.bak-before-opt-prefix-20261110T124433Z` (3194 B; new file
3220 B). `sh -n` passed.

### Why this layer, not `customer_env.sh` + `boot.sh`

The live `root_boot.sh` hard-sets `PATH` immediately before it spawns the
persistent `telnetd`. A `customer_env.sh` export would be overridden, and
`/usr/local/bin` does not exist to bind-mount over. `root_boot.sh` owns the
login shell's environment, so its PATH line is the root cause.

## Cold boot, USB removed

Evidence: `evidence/install/proof-2.txt`.

| Check | Result |
| :--- | :--- |
| `/media` and `/media/sda1` | empty / absent (no USB) |
| login `PATH` | `…:/mtd_rwarea/apdat/opt/bin` |
| `root_boot.sh:12` | same PATH |
| `command -v lsblk` | `/mtd_rwarea/apdat/opt/bin/lsblk` |
| `lsblk` | lists devices |
| `root_boot.ready` | `READY … uptime=12.08` |
| uptime at check | 169.28 s (no reboot loop) |

The `READY` marker is written by the persistence hook at uptime ~12 s, i.e.
before the check; the unit stayed up.

## Manual-run artifact (not a boot issue)

Running `sh root_boot.sh` on a live system prints
`cp: cannot create regular file '/tmp/persist/busybox': Text file busy`, because
the running telnetd *is* that file. At boot `/tmp/persist` is fresh, so the copy
succeeds (proven by the `READY` marker on this cold boot). Do not use a manual
re-run as the acceptance test.

## What this enables

Any static tool dropped in `/mtd_rwarea/apdat/opt/bin` is on `PATH` after a
USB-less boot. That is the install seam for Dropbear and future tools.

## Next

Dropbear on a non-default port, key-only, host key and `authorized_keys`
under `opt/etc`, one firewall ACCEPT rule, started after the boot firewall.
Needs a static build toolchain (no compiler on the TV).

## Safety

Only `/mtd_rwarea/apdat/root_boot.sh` and `opt/` were written. No flash, boot,
or partition writes. Backup exists; USB autorun remains the recovery path.
