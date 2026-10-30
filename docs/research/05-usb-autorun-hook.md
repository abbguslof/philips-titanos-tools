# USB autorun hook

Status: **VERIFIED** on hardware. This is the path that gives an ephemeral root
shell from a cold boot.

## The chain

```text
/etc/init.d/S21idtv.sh
  -> sources /mtd_apexe/board/run.sh as root
    -> runs /mtd_apexe/board/quick_debug/menu auto &
      -> waits for /tmp/ntkdriver_completed
      -> finds /media/sda1/autoscript*.txt
      -> sleeps 30 seconds (unless called with "auto skip")
      -> eval's each line as root in system_u:system_r:initrc_t
```

Key source locations in the shipped `ap0` partition:

| File | Lines | Behaviour |
| :--- | :--- | :--- |
| `board/run.sh` | 738–742 | Starts `quick_debug/menu auto &`. |
| `board/quick_debug/menu` | 10–22 | Waits for `/tmp/ntkdriver_completed`, then `find /media/sda1 -maxdepth 1 -type f -name "autoscript*.txt"`. |
| `board/quick_debug/menu` | ~128 | `eval "$cleaned_line"` for every non-directive line. |
| `rootfs/etc/init.d/S21idtv.sh` | 11–23 | Sources `/mtd_apexe/board/run.sh`, then `/media/sda1/board/run.sh`, then `/media/sda/board/run.sh`. |
| `rootfs/usr/share/usb/autoscript.sh` | 50–53 | Mounts an **unlabelled** partition at `/media/$1` (for example `/media/sda1`). |

## The 30-second delay

`menu auto` sleeps 30 seconds after finding the script and before evaluating it.
The root port therefore opens roughly **36 seconds after power-on** (the marker
appears around 5–6 seconds). If you test at 10 seconds, it looks broken.

The `menu` script also accepts `auto skip`, which skips the delay, but
`run.sh` calls plain `auto`.

## The label rule

`autoscript.sh` uses the partition label as the mount directory:

- **Empty label** -> `dir=$1` -> `/media/sda1` -> the `find` matches.
- **Label `PHILIPS`** -> `/media/PHILIPS` -> the hardcoded `find /media/sda1`
  misses it.

This is why the root stick must be **unlabelled**. SAM `Download from USB`, on
the other hand, expects a FAT32 volume labelled `PHILIPS`. These are two
different USB workflows; do not reuse one stick for both without reformatting.
See the [glossary](../../GLOSSARY.md#usb-workflows).

## BusyBox argv[0] rule

The rootfs has no `telnetd` and no `nc`. Ship a static armhf BusyBox. BusyBox
resolves applets from `argv[0]`, so the copied file must be named `busybox`:

```sh
/bin/cp /media/sda1/busybox-armhf /tmp/busybox
/bin/chmod +x /tmp/busybox
/tmp/busybox telnetd -p 2323 -l /bin/sh
```

Copying it as `/tmp/bb` and running `/tmp/bb telnetd` fails with
`bb: applet not found`, even though the applet table contains `telnetd`.

## The v7 payload

`payloads/autoscript.autoroot.txt` is one line:

```sh
/bin/sh /media/sda1/autoroot.sh >>/media/sda1/autoroot.log 2>&1
```

`payloads/autoroot.sh` then:

1. writes diagnostics to `autoroot-diag.txt`;
2. copies BusyBox to `/tmp/busybox`, verifies the `telnetd` applet;
3. inserts one `iptables -w 5` rule for TCP `:2323`;
4. starts `busybox telnetd -p 2323 -l /bin/sh`;
5. writes `READY` only when `netstat` confirms the listener.

It does not use `pkill`, and it does not flush the firewall.

## Build the stick

```bash
sudo ./tools/autoroot_usb.py --device /dev/sdX --host <TV_IP>
```

The tool enforces MBR + one FAT32 partition, **empty label**, stages the three
files, verifies SHA-256, and remounts read-only to verify again.

Detailed steps: [USB autoroot guide](../guides/usb-autoroot.md).

## Evidence

- `evidence/usb-autoroot/v4-shell-uid0/` — first successful local shell test.
- `evidence/usb-autoroot/v7-autoroot-success/` — full cold-boot success,
  `READY`, listener, `uid=0`.
- `evidence/usb-autoroot/v6-regression/` — the run that failed because the
  stick was missing `busybox-armhf`; useful for diagnosing "connection refused".
