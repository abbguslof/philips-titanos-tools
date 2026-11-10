# Dropbear SSH on the install prefix

Status: **VERIFIED** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-10. SSH survives a cold boot with the USB
removed.

## Build

Zig 0.17.1, target `aarch64-linux-musl`, Dropbear commit `17549ea6`, bundled
libtom, no zlib/syslog/pam. Two `default_options.h` macros carry the
`/mtd_rwarea/apdat/opt/bin` prefix. Full record:
`evidence/install/ssh-build.txt`.

```
dropbearmulti  729,504 B  aarch64 static-pie  no INTERP/NEEDED
sha256 0f1fa428c012ea977335e504c882c9e9205f86f6c6a172c271ca2d5a98c7699c
```

## Install

| Path | Purpose |
| :--- | :--- |
| `opt/bin/dropbearmulti` | server and `dropbearkey` applet |
| `opt/etc/dropbear/ed25519_host_key` | host key, generated on-device, 600 |
| `opt/root_home/.ssh/authorized_keys` | client key(s), 600 |
| `opt/etc/profile.d/opt-bin.sh` | login-shell PATH drop-in |
| `opt/var/dropbear.log` | server log |
| `opt/disabled` | kill switch (any file) |

## Three failures and fixes

1. **authorized_keys rejected when outside the home dir.** With
   `-D /mtd_rwarea/apdat/opt/etc/ssh`, Dropbear checks every path component.
   `apdat` is 777, so it refused with
   `... opt/etc must be owned by user or root, and not writable by group or
   others`. The default `~/.ssh` inside a controlled home fixes this.

2. **PATH missing `opt/bin`.** `/etc/profile` resets `PATH`, and Dropbear sets
   `DEFAULT_ROOT_PATH` for non-interactive commands. Two changes cover both
   cases: a bind mount of `opt/etc/profile.d` over `/etc/profile.d` for login
   shells, and a rebuild with `DEFAULT_ROOT_PATH`/`DEFAULT_PATH` prefixed by
   `opt/bin` for `ssh host 'cmd'`.

3. **Boot resets permissions.** `/mtd_apexe/board/run.sh:587` runs
   `chmod 777 -R /mtd_apdat/` on every boot. A bind-mounted `/root` becomes
   group/other-writable, and Dropbear rejects `/root/.ssh`. The fix mounts a
   700 tmpfs over `/root` at boot and copies `authorized_keys` into it (600).
   The tmpfs sits outside `apdat`, so the vendor `chmod` cannot reset it.

`evidence/install/ssh-live.txt` records all three.

## Cold boot

Evidence: `evidence/install/ssh-boot.txt`.

| Check | Result |
| :--- | :--- |
| `/media/sda1` | absent (no USB) |
| `/root` | `tmpfs … mode=700` |
| `/root/.ssh` | 700, key 600 |
| `command -v lsblk` | `/mtd_rwarea/apdat/opt/bin/lsblk` |
| `root_boot.ready` | `READY … uptime=12.41` |
| SSH | `uid=0(root)`, key auth succeeded |

## Persistence

`root_boot.sh` runs after the driver marker and a 5 s delay:

- `payloads/root_boot.opt-block.sh` mounts the 700 tmpfs on `/root`, copies
  `authorized_keys`, and sets 700/700/600;
- the same block seeds and bind-mounts `opt/etc/profile.d`, then re-asserts
  its modes;
- it inserts the `:2222` firewall ACCEPT rules;
- it starts Dropbear unless `opt/disabled` exists or `:2222` is already
  listening.

Backups: `root_boot.sh.bak-before-ssh-20261110T125842Z` and
`root_boot.sh.bak-before-ssh-tmpfs-*`. `sh -n` passed on the workstation and
on the device.

## Security

- Publickey only (`-s`). Password auth stays off.
- Port 2222, LAN only. Do not forward it.
- Telnet `:2323` stays up as the recovery shell.
- Kill switch: create `opt/disabled` and reboot.
- `apdat` is world-writable, so any local user who can write it can change
  `opt/root_home/.ssh/authorized_keys` before the boot copy. The tmpfs copy
  fixes the permissions Dropbear checks; it does not fix the source. Treat
  `apdat` as a trusted path.

## Rollback

```sh
cp -a /mtd_rwarea/apdat/root_boot.sh.bak-before-ssh-tmpfs-<stamp> \
      /mtd_rwarea/apdat/root_boot.sh
# kill the running server by PID, then cold boot
```

## Open

Telnet remains plaintext. Disable it once you no longer need the fallback.
