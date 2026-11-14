# Persistent root

Status: **VERIFIED on hardware** on the tested `55PUS8000/12` (root after a
cold boot with the USB removed). The redacted capture is in
[evidence/persistence/output.txt](../../evidence/persistence/output.txt). The
`/swdl` fallback is **REPORTED**; see the
[variant note](../research/24-swdl-telnet-persistence-2026-11-11.md).

An external [77OLED760/12 report](../../evidence/tpn258e-77oled760/) also
records a successful USB-less cold boot using the `/swdl` hook on TPN258E
firmware `058.010.032.001`, with selected boot-log evidence. Status: **REPORTED**.

The hook is firmware-specific. This guide was verified on `55PUS8000/12`.
Other models may use a different hook, so check the live firmware first.
Reports and PRs for other models are welcome.

The payload lives on the writable `apdat` partition. The boot hook is either
`customer_env.sh` on `apdat` or, on the reported firmware variant, a wrapper at
`/swdl/telnet/telnetd` on the writable `/swdl` partition. Neither modifies the
read-only rootfs or the bootloader.

## Start from the USB root shell

Complete [USB autoroot](usb-autoroot.md) first. You need `/tmp/busybox` to be
present; it is the binary that the USB payload is already running from.

Before installing, check which boot hook your firmware reads:

```sh
grep -n customer_env.sh /mtd_apexe/board/run.sh
grep -n '/swdl/telnet/telnetd' /mtd_apexe/board/run_custom_impl.sh
```

A match in the first command means the documented `customer_env.sh` path
applies. If the first command prints nothing but the second matches, the
installer will use the [`/swdl/telnet/telnetd` fallback](../research/24-swdl-telnet-persistence-2026-11-11.md).
If neither matches, stop and report both outputs with your firmware version.

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

Both variants always get the payload on `apdat`:

```text
/mtd_rwarea/apdat/busybox              static armhf BusyBox
/mtd_rwarea/apdat/root_boot.sh         boot script
```

If `run.sh` sources `customer_env.sh`, it also writes:

```text
/mtd_rwarea/apdat/customer_env.sh      vendor hook + one appended line
/mtd_rwarea/apdat/customer_env.sh.bak  backup if the file already existed
```

The appended line is:

```sh
[ -f /mtd_rwarea/apdat/root_boot.sh ] && /bin/sh /mtd_rwarea/apdat/root_boot.sh &
```

It runs `restorecon` on `busybox`, `root_boot.sh`, and `customer_env.sh` so
they keep the `idtv_data_t` label.

If `run.sh` no longer sources `customer_env.sh` but `run_custom_impl.sh` has the
`/swdl/telnet/telnetd` check, the installer writes only this extra file:

```text
/swdl/telnet/telnetd                   wrapper that backgrounds root_boot.sh
/swdl/telnet/telnetd.bak               backup if a vendor file already existed
```

The `/swdl` wrapper is:

```sh
#!/bin/sh
[ -f /mtd_rwarea/apdat/root_boot.sh ] && /bin/sh /mtd_rwarea/apdat/root_boot.sh &
```

It does not run `restorecon` on the `/swdl` wrapper; that path has a different
policy context. See the
[`/swdl` variant note](../research/24-swdl-telnet-persistence-2026-11-11.md).

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
grep -n customer_env.sh /mtd_apexe/board/run.sh
grep -n '/swdl/telnet/telnetd' /mtd_apexe/board/run_custom_impl.sh
ls -l /swdl/telnet/telnetd
```

If `root_boot.log` has no entry for the fresh boot, the installer picked a
hook this firmware does not read. The `grep` output tells you which variant
applies. Do not keep rebooting; fix the hook first.

The TV still boots normally if the hook fails; the hook is a background script,
not an init replacement.

## Remove persistence

Remove the hook that the installer selected:

```sh
# customer_env.sh variant:
sed -i '/root_boot.sh/d' /mtd_rwarea/apdat/customer_env.sh

# /swdl/telnet/telnetd variant:
rm -f /swdl/telnet/telnetd
rmdir /swdl/telnet 2>/dev/null || true
```

Then remove the shared `apdat` payload:

```sh
rm -f /mtd_rwarea/apdat/root_boot.sh /mtd_rwarea/apdat/busybox \
      /mtd_rwarea/apdat/root_boot.log /mtd_rwarea/apdat/root_boot.ready \
      /mtd_rwarea/apdat/root_boot.ready.failed
```

If `/swdl/telnet/telnetd.bak` exists, the installer saved a pre-existing file
there. Inspect it before deleting or restoring it.

Cold boot. If this project created `customer_env.sh` and it contains nothing
else, you can remove it too. If the file existed before, keep the rest of its
content and delete only the hook line. See
[restore to stock](restore-to-stock.md).
