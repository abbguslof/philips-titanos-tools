# Install prefix (on-TV tools)

Goal: add tools without touching the read-only rootfs. Everything lives under
`/mtd_rwarea/apdat/opt` (rw ext4, p31) and is activated by PATH or a boot hook.

## Layout

```
/mtd_rwarea/apdat/opt/
├── bin/            static binaries + wrappers
├── etc/            config, host keys, authorized_keys
├── lib/            only if a tool is dynamic
├── var/            logs/state
└── manifest.sha256 sha256 of installed files
```

## ABI

TV userspace is 32-bit ARM EABI5 (armhf); the kernel is aarch64. Build **static**
binaries (armhf or aarch64). There is no compiler on the TV.

## Build `lsblk`

`tools/install/lsblk.c` is a freestanding static armhf `lsblk` that reads
`/proc/partitions`. No libc, no dynamic loader, no division.

```sh
LLD=${LLD:-ld.lld}   # set this if lld is not on PATH
clang --target=arm-linux-gnueabihf -march=armv7-a \
  -nostdlib -nostartfiles -fno-stack-protector -fno-builtin -ffreestanding \
  -static -no-pie -O2 -Wall -Wextra -Wno-unused-parameter -Wno-unused-function \
  -fuse-ld=lld --ld-path="$LLD" -Wl,-e,_start \
  -o dist/armhf/lsblk tools/install/lsblk.c
```

## Install (live root shell)

```sh
mkdir -p /mtd_rwarea/apdat/opt/{bin,etc,lib,var}
/usr/bin/wget -q -O /mtd_rwarea/apdat/opt/bin/lsblk http://192.0.2.44:8000/lsblk
chmod 0755 /mtd_rwarea/apdat/opt/bin/lsblk
sha256sum /mtd_rwarea/apdat/opt/bin/lsblk > /mtd_rwarea/apdat/opt/manifest.sha256
PATH=/mtd_rwarea/apdat/opt/bin:$PATH lsblk
```

## Persistence

`PATH` survives because `/mtd_rwarea/apdat/root_boot.sh:12` appends
`/mtd_rwarea/apdat/opt/bin` before it starts the persistent `telnetd`. Verified
with the USB removed on 2026-11-10 (`evidence/install/proof-2.txt`,
`docs/research/22-opt-prefix-persistence-2026-11-10.md`).

## Dropbear (SSH)

Built with zig 0.17.1 for `aarch64-linux-musl`; see
`evidence/install/ssh-build.txt`. Two non-obvious requirements:

1. `authorized_keys` must be inside the user's home, because Dropbear checks
   every path component otherwise and `apdat` is 777. Keep it in
   `opt/root_home/.ssh/` and bind-mount that over `/root`.
2. Login shells and non-interactive commands get different PATHs. Bind
   `opt/etc/profile.d` over `/etc/profile.d` (login shells) and build with
   `DEFAULT_ROOT_PATH` prefixed by `opt/bin` (`ssh host 'cmd'`).

Start (key-only):

```sh
"$OPT/bin/dropbearmulti" dropbear -F -p 2222 \
  -r "$OPT/etc/dropbear/ed25519_host_key" -s
```

Persisted in `root_boot.sh`; kill switch: create `opt/disabled`. Details:
`docs/research/23-dropbear-ssh-2026-11-10.md`.
