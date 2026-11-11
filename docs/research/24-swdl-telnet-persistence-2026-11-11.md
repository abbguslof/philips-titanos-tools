# Firmware variant: `/swdl/telnet/telnetd` persistence hook

Status: **REPORTED on hardware** by an external contributor (Pedram) on
2026-11-11, on `55PUS8450/12`, chassis `TPN256E`, firmware
`TPN256E_V056.010.032.001`. Not independently reproduced by this repo's
maintainer. Subsequent USB autoroot logs confirm the unit and its USB root path,
but they do not include the USB-less `root_boot.log`, so the persistence result
stays REPORTED. The vendor seam itself is **VERIFIED statically** in the
extracted `ap0` (`run_custom_impl.sh`) and was already listed as a vendor update
surface in [webview and IPC](13-webview-launcher-ipc.md#vendor-swdl-overlay) and
[app framework](14-app-framework.md#vendor-customization-hooks).

## Summary

On this firmware, `run.sh` does not source `/mtd_apdat/customer_env.sh`, so the
documented [`customer_env.sh` persistence](06-persistence-customer-env.md)
cannot survive a cold boot. The vendor customization chain still executes
`/swdl/telnet/telnetd` when the file exists and is executable. A one-line
wrapper there starts the existing `root_boot.sh`, which waits out the boot
firewall. Pedram reported a cold boot with the USB stick removed working for
both telnet `:2323` and Dropbear SSH `:2222`.

`payloads/persist_root.sh` now detects which hook the live firmware reads and
installs the matching trigger.

## Target

|          | This report                | Maintainer's tested model  |
| :------- | :------------------------- | :------------------------- |
| Model    | 55PUS8450/12               | 55PUS8000/12               |
| Chassis  | TPN256E                    | TPA256E / TPN256E          |
| Firmware | `TPN256E_V056.010.032.001` | `TPA256E_V056.002.236.191` |
| Root partition | `mmcblk0p19`         | `mmcblk0p20`               |
| `customer_env.sh` in `run.sh` | absent       | present                    |
| `/swdl/telnet/telnetd` check  | present      | present                    |

The model and firmware differ from the tested unit. Treat this as a firmware
variant, not a replacement for the documented path. The
`/swdl/telnet/telnetd` check is present in the extracted `ap0` used by this
repo, so the same fallback is available on the target if `customer_env.sh`
disappears in a later update.

## Diagnose before installing

Check which hook the live firmware reads:

```sh
grep -n customer_env.sh /mtd_apexe/board/run.sh
grep -n '/swdl/telnet/telnetd' /mtd_apexe/board/run_custom_impl.sh
```

- The first command prints the `source` block on the tested model.
- The second prints the vendor check on both the tested model and the reported
  variant.
- If the first prints nothing, do not append to `customer_env.sh`. The file
  will look installed but will never run.

The installer now runs this detection and aborts without writing if neither
pattern is found.

## How the absence was confirmed

The report records these steps on the affected unit:

1. The installer ran without error. It wrote `apdat/busybox`,
   `apdat/root_boot.sh`, and the `customer_env.sh` line.
2. Running `sh /mtd_rwarea/apdat/root_boot.sh` from a live root shell worked
   every time: `telnetd`/Dropbear started and `root_boot.ready` was written.
3. A real cold boot with the USB stick removed brought up neither `:2323` nor
   `:2222`.
4. Pedram regained root with the USB autoroot stick. `root_boot.log` had no
   new entry; its last uptime was from the earlier manual run, not the fresh
   boot.
5. `grep -n customer_env /mtd_apexe/board/run.sh` returned nothing.
6. The installed files themselves checked out: content, `sh -n`, and the
   `/mtd_apdat` symlink. The only missing piece was the `run.sh` source line.

## Additional autoroot evidence

Pedram supplied two USB autoroot logs from the same unit. They confirm
`uid=0(root)` with the `initrc_t` context, a USB stick mounted at
`/media/sda1`, and `telnetd` on `:2323` across two boots. The redacted excerpt
is in [evidence/tpn256e-variant](../../evidence/tpn256e-variant/).

The logs also show `root=/dev/mmcblk0p19`; the tested model uses
`mmcblk0p20`. Treat partition numbers as firmware-specific.

The logs do not include `root_boot.log` or the `/swdl` wrapper. The USB-less
persistence result stays REPORTED until that capture arrives.

## The vendor seam

`run.sh` calls `run_n22070_vewd()`, which sources `run_custom.sh` and runs
`run_custom_main()`. That chain reaches `run_custom_impl.sh` and
`run_custom_impl_run()`, which contains:

```sh
if [ -x /swdl/telnet/telnetd ]; then
    /swdl/telnet/telnetd
fi
```

`/swdl` is `/dev/nvt-part-name/sw_dl`, a writable ext4 partition. It is
distinct from `apdat`; see [flash layout](02-flash-layout-and-partitions.md) and
the [partition map](../reference/partition-map.md).

The stock firmware supplies the check. The executable at that path is not part
of the installer's `apdat` payload; this toolkit writes a small wrapper there.
A unit may have a vendor file at that path, so the installer backs up an
existing file to `/swdl/telnet/telnetd.bak` before replacing it. This is a
vendor service/update seam. It does not provide remote access.

## Installer behavior

| Hook selected | Files written | Notes |
| :--- | :--- | :--- |
| `customer_env.sh` | `apdat/busybox`, `apdat/root_boot.sh`, one line appended to `apdat/customer_env.sh` | The original verified path. |
| `/swdl/telnet/telnetd` | `apdat/busybox`, `apdat/root_boot.sh`, `/swdl/telnet/telnetd` wrapper | No `customer_env.sh` edit. |

The wrapper is:

```sh
#!/bin/sh
[ -f /mtd_rwarea/apdat/root_boot.sh ] && /bin/sh /mtd_rwarea/apdat/root_boot.sh &
```

The wrapper adds no boot logic. `root_boot.sh` already waits for
`/tmp/ntkdriver_completed` (60 s cap) plus 5 seconds, then applies the firewall
rule and starts `telnetd`. That delay is required because
`run_custom_impl_run()` runs well before `iptables_conf.sh`.

## Cold-boot result (reported)

The report states:

- the USB stick was absent at boot;
- `telnetd` on `:2323` and Dropbear SSH on `:2222` both came up without manual
  intervention;
- `root_boot.log`'s last entry had an uptime in the tens of seconds, matching
  the fresh boot, so the wrapper (not a leftover process) triggered it;
- a later USB autoroot run still reported a clean
  `SUCCESS: telnetd listening on :2323`.

The later autoroot logs cover the USB-stick boots only. They do not include
`root_boot.log`. The cold-boot result stays **REPORTED**, not independently
verified.

## Security and limits

- `/swdl` is a writable vendor update surface. Treat it as a trusted path, like
  `apdat`.
- The wrapper starts a root payload from `apdat`; both paths must remain under
  your control.
- The wrapper adds no firewall flush and no `pkill`. The existing
  `root_boot.sh` handles the ordering.
- The installer does not run `restorecon` on the `/swdl` wrapper. Pedram's
  method ran the wrapper with the label the file inherited from `/swdl`;
  nobody tested `restorecon` there. `apdat`'s `idtv_data_t` policy does not
  apply.
- The hook writes a file outside `apdat`, so restore must remove it too.
- This report did not test factory-reset or vendor-update behavior for files
  on `/swdl`.

## Restore

```sh
rm -f /swdl/telnet/telnetd

# Only if the installer backed up a pre-existing vendor file:
# ls -l /swdl/telnet/telnetd.bak
# mv /swdl/telnet/telnetd.bak /swdl/telnet/telnetd

rm -f /mtd_rwarea/apdat/root_boot.sh /mtd_rwarea/apdat/busybox \
      /mtd_rwarea/apdat/root_boot.log /mtd_rwarea/apdat/root_boot.ready \
      /mtd_rwarea/apdat/root_boot.ready.failed
rmdir /swdl/telnet 2>/dev/null || true
```

Cold boot afterwards. If you lose the shell, the USB autoroot stick is the
recovery path. See [restore to stock](../guides/restore-to-stock.md).

## Other `/swdl` seams

`run_custom_impl_run()` also checks `/swdl/ftp/tcpsvd` and `/swdl/ftp/ftpd` for
an FTP daemon, plus the bind-mount overlays listed in
[app framework](14-app-framework.md#vendor-customization-hooks). Persistence
does not need them, and this report did not test them.

## Credit

Reported and tested on hardware by **Pedram** on 2026-11-11, including the
negative result for `customer_env.sh`, the `/swdl` replacement, and the
USB-less cold-boot check. Thanks for sending it back upstream.
