# Persistence evidence

Status: **hardware-verified in the research session, public capture pending.**

After installing `payloads/persist_root.sh`, removing the USB stick, and cold
booting, the TV returned an interactive `uid=0` root shell on `:2323`. The
public evidence set is waiting for a clean redacted capture from the TV shell.

## Capture procedure

Run this **inside the TV's `nc` session**, not in the workstation shell. The
first line must show `uid=0(root)`, and the `cmdline` must contain
`root=/dev/mmcblk0p20`.

```sh
BASE=/mtd_rwarea/apdat
{
  echo "=== date ==="; date
  echo "=== id ==="; id
  echo "=== uptime ==="; cat /proc/uptime
  echo "=== cmdline ==="; cat /proc/cmdline
  echo "=== selinux ==="; cat /sys/fs/selinux/enforce
  echo "=== boot markers ==="; ls -l /tmp/ntkdriver_completed /tmp/persist/busybox 2>&1
  echo "=== apdat ==="; ls -l "$BASE"
  echo "=== customer_env ==="; cat "$BASE/customer_env.sh"
  echo "=== root_boot head ==="; sed -n '1,40p' "$BASE/root_boot.sh"
  echo "=== root_boot log ==="; cat "$BASE/root_boot.log"
  echo "=== ready ==="; cat "$BASE/root_boot.ready" 2>&1
  echo "=== netstat ==="; netstat -ltn
  echo "=== iptables ==="; iptables -S INPUT
  echo "=== mounts ==="; cat /proc/mounts
} 2>&1
```

Paste the output into `evidence/persistence/output.txt`, then redact the TV IP
and any device identifiers before committing.

## Invalid prior capture

`usbdump/autoscriptproof/v8-presist/output.txt` was accidentally run in the
workstation shell. It shows `uid=1000`, the host kernel command line, and no
`/mtd_rwarea`, so it is not included. Do not use it as TV evidence.
