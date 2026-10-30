# USB autoroot: ephemeral root shell

Status: **VERIFIED** on `55PUS8000/12`, firmware `TPA256E_V056.002.236.191`.

This gives an interactive `uid=0` shell on TCP `:2323` from a cold boot. It
writes nothing to flash. Restore is: remove the stick, cold boot.

## Requirements

- A spare USB stick (all data will be erased).
- A Linux host with `sfdisk`, `mkfs.fat`, `mount`, and Python 3.
- The TV's LAN address.
- Physical access to the TV's USB port and AC plug.

## Build the stick

```bash
cd philips-titan-tools
sudo ./tools/autoroot_usb.py --device /dev/sdX --host <TV_IP>
```

Use the **whole disk** (`/dev/sdb`), not a partition (`/dev/sdb1`). The tool
prints the model/size and asks for `YES`. It creates:

- MBR partition table;
- one FAT32 partition with an **empty label**;
- `autoscript.txt`, `autoroot.sh`, `busybox-armhf`;
- `AUTOROOT-README.txt` and `autoroot.sha256`.

It verifies SHA-256, unmounts, remounts read-only, and verifies again.

> The empty label is mandatory. An unlabelled partition mounts at `/media/sda1`;
> a labelled one mounts at `/media/<LABEL>` and the hardcoded `find` misses it.

## Cold boot

1. Unplug the TV from AC and wait 10 seconds.
2. Insert the stick into the USB port that enumerates as `sda` on the TV.
   If another USB disk is present, the stick may become `sdb` and the hardcoded
   `/media/sda1` lookup will miss it.
3. Plug the TV back in.
4. Wait at least **45 seconds**. `quick_debug/menu auto` sleeps 30 seconds after
   it finds the script, and the script itself needs a few seconds to start the
   listener.

## Connect

The TV's BusyBox `telnetd` opens with IAC negotiation. Inetutils `telnet` may
show nothing. Use a raw client:

```bash
nc <TV_IP> 2323
# or
socat -,raw,echo=0 tcp:<TV_IP>:2323
```

Then:

```sh
id
```

Expected:

```text
uid=0(root) gid=0(root) groups=0(root) context=system_u:system_r:initrc_t
```

Non-interactive check:

```bash
timeout 6 bash -c 'exec 3<>/dev/tcp/<TV_IP>/2323; printf "id\n" >&3; cat <&3'
```

## What the payload does

`autoscript.txt` runs `autoroot.sh`, which:

1. logs `id`, `cmdline`, `ttyS0` counters, and media mounts to
   `autoroot-diag.txt`;
2. copies `busybox-armhf` to `/tmp/busybox` and checks the `telnetd` applet;
3. inserts `iptables -w 5 -I INPUT 1 -p tcp --dport 2323 -j ACCEPT`;
4. starts `busybox telnetd -p 2323 -l /bin/sh`;
5. writes `READY` only when `netstat` confirms the listener.

It does not use `pkill`; it does not flush the firewall.

## If it fails

Pull the stick and inspect these files on it:

| File | Meaning |
| :--- | :--- |
| `autoroot.log` | Script output. |
| `autoroot-diag.txt` | Success/failure diagnostics, `netstat`, `ps`, `iptables`. |
| `READY` | Listener confirmed. |
| `FAILED` | Reason the listener did not come up. |

Common causes:

- **No `autoroot.log`** — the stick was labelled, not mounted at `/media/sda1`,
  or inserted after the 6-second `find`.
- **`FAILED` with "missing busybox"** — the stick was missing
  `busybox-armhf`; rebuild it with the tool.
- **`telnetd` started but LAN connection is refused** — the firewall rule did not
  apply. Check `iptables -S INPUT` in the diag file.
- **Nothing until ~36 s** — the 30-second menu sleep is normal.

The [v6 evidence](../../evidence/usb-autoroot/v6-regression/) is a real example
of a stick missing the busybox: the script ran, but `telnetd` never started.

## Restore

Pull the stick and cold boot. The only state is `/tmp/busybox` (tmpfs) and the
running processes; both disappear on reboot. Nothing is written to flash.

For persistence, see [persistent root](persistent-root.md). For the opposite
direction, see [restore to stock](restore-to-stock.md).
