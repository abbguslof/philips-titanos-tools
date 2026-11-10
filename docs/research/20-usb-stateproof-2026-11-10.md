# USB stateproof and non-reset autoscript

Status: **VERIFIED / OPEN** on `55PUS8000/12`, firmware
`TPA256E_V056.002.236.191`, 2026-11-10.

Step 1 only. The Pi is unplugged; there is no serial. Output is the file the
autoscript writes to `/media/sda1` plus the live `:2323` shell.

## Payload

`payloads/autoscript.stateproof.txt:1` (one LF-terminated line):

```sh
/bin/cp /media/sda1/busybox-armhf /tmp/busybox; /bin/chmod 0755 /tmp/busybox; /tmp/busybox setsid /bin/sh -c '{ echo "=== boot ==="; /bin/date; /usr/bin/id; echo "--- cmdline ---"; /bin/cat /proc/cmdline; echo "--- mounts ---"; /bin/cat /proc/mounts; } >>/media/sda1/proof.txt 2>&1' </dev/null >/dev/null 2>&1 &
```

Design against the hook: `menu` evals each line (`05-usb-autorun-hook.md:24`)
after a 30 s delay (`:30`). The line returns 0 immediately (`&`), the worker is
`setsid`-detached, and its stdio is `/dev/null` so it cannot hold the menu's
pipe open. No `exec`; the menu shell is not replaced.

## Evidence

| Fact | Source |
| :--- | :--- |
| Exactly one boot block | `evidence/usb-autoroot/v8-stateproof/run-meta.txt:2` |
| Eval timestamp 12:27:23 | `evidence/usb-autoroot/v8-stateproof/proof.txt:2` |
| Uptime 126.31 s at 12:28:53 | `run-meta.txt:5-6` |
| `uid=0(root)` | `proof.txt:3` |
| cmdline `console=ttynull … root=/dev/mmcblk0p20 ro` | `proof.txt:5` |
| `/` is `squashfs ro` | `proof.txt:7` |
| `apdat /mtd_rwarea ext4 rw` | `proof.txt:29` |
| `/media/sda1 vfat rw` | `proof.txt:31` |

Eval at ~36 s after power-on (30 s menu delay + marker) and uptime 126 s at
check time means the unit did not reboot after the eval. Boot blocks = 1.

## Result

- Self-reporting: **VERIFIED**. One block per boot with `id`, cmdline, mounts.
- `RESET(33)` recurrence: **not observed on this boot**; the unit stayed up.
- Exact cause of the original `RESET(33)`: **UNKNOWN**. Not documented in the
  repo and not observable without serial. The two block/hang mechanisms
  (inherited stdio, foreground eval) are removed by this payload.
- Recurrence rate: UNKNOWN (n=1 boot). One more cold boot would make it n=2.

## Recorded for Step 2 (not acted on)

The same proof already captures the boot filesystem posture:
`/` is `squashfs ro` (`proof.txt:7`), `apdat`/`mtd_rwarea` is `ext4 rw`
(`proof.txt:29`), and a custom root is bind/loop-mounted at
`/tmp/freetitan-root` from `loop6` (squashfs ro, `proof.txt:36`) and `loop5`
(ext4 rw, `proof.txt:41-47`). Step 2 is not started.

## Safety

Only `/media/sda1/proof.txt` and `/tmp` are written. No flash, boot, or
partition writes. Restore is removing the stick and cold booting.
