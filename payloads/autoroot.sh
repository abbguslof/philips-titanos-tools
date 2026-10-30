#!/bin/sh
# Titan OS one-shot root payload.
#
# Runs as root from:
#   /mtd_apexe/board/run.sh -> quick_debug/menu auto -> autoscript.txt
# The menu waits for /tmp/ntkdriver_completed, finds /media/sda1/autoscript*.txt,
# sleeps 30 seconds, then evaluates each line as root in initrc_t.
#
# This payload writes nothing to flash. Restore = remove the USB stick and cold
# boot the TV. It starts a root shell on TCP :2323 and records why it did or did
# not come up.

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export PATH

USB=/media/sda1
PORT=2323
LOG=$USB/autoroot.log
DIAG=$USB/autoroot-diag.txt
READY=$USB/READY
FAILED=$USB/FAILED

# Also log when the script is run by hand instead of via autoscript.txt.
exec >>"$LOG" 2>&1

echo "=== autoroot start ==="
echo "date: $(date 2>/dev/null)"
echo "uptime: $(cat /proc/uptime 2>/dev/null)"
echo "id: $(id 2>/dev/null)"
echo "cmdline: $(cat /proc/cmdline 2>/dev/null)"
echo "serial: $(cat /proc/tty/driver/serial 2>/dev/null)"
echo "media mounts:"
grep ' /media' /proc/mounts 2>/dev/null

mkdir -p "$USB" 2>/dev/null
rm -f "$READY"
: > "$FAILED"

die() {
    echo "FATAL: $*"
    echo "$*" > "$FAILED"
    exit 1
}

[ -f "$USB/busybox-armhf" ] || die "missing $USB/busybox-armhf"
/bin/cp "$USB/busybox-armhf" /tmp/busybox || die "copy busybox failed"
/bin/chmod 0755 /tmp/busybox || die "chmod busybox failed"
/tmp/busybox --list 2>/dev/null | /bin/grep -qx telnetd || die "busybox has no telnetd applet"

# Open only the root port. -w waits for the xtables lock held by the DLNA,
# update, and telemetry daemons during boot. The IPv4 rule is the important
# one; the IPv6 rule is best effort because busybox telnetd binds :: by default.
if [ -x /usr/sbin/iptables ]; then
    /usr/sbin/iptables -w 5 -I INPUT 1 -p tcp --dport "$PORT" -j ACCEPT || echo "WARN: iptables -I failed"
else
    echo "WARN: /usr/sbin/iptables missing"
fi
if [ -x /usr/sbin/ip6tables ]; then
    /usr/sbin/ip6tables -w 5 -I INPUT 1 -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null || echo "WARN: ip6tables -I failed"
fi

# Do not use pkill. If the menu evaluates this twice, the second pass must not
# kill the listener the first pass created.
if /bin/netstat -ltn 2>/dev/null | /bin/grep -qE "[:.]$PORT[[:space:]]"; then
    echo "port $PORT already listening"
else
    /tmp/busybox telnetd -p "$PORT" -l /bin/sh &
    echo "telnetd pid $!"
fi

n=0
while [ "$n" -lt 10 ]; do
    if /bin/netstat -ltn 2>/dev/null | /bin/grep -qE "[:.]$PORT[[:space:]]"; then
        break
    fi
    /bin/sleep 1
    n=$((n + 1))
done

if /bin/netstat -ltn 2>/dev/null | /bin/grep -qE "[:.]$PORT[[:space:]]"; then
    {
        echo "=== success ==="
        echo "date: $(date 2>/dev/null)"
        echo "uptime: $(cat /proc/uptime 2>/dev/null)"
        id
        /bin/netstat -ltn
        /bin/ps w
        /usr/sbin/iptables -w 5 -S INPUT 2>/dev/null
    } > "$DIAG" 2>&1
    echo "READY $(date 2>/dev/null)" > "$READY"
    rm -f "$FAILED"
    echo "SUCCESS: telnetd listening on :$PORT"
else
    {
        echo "=== failure ==="
        /bin/netstat -ltn
        /bin/ps w
        /bin/dmesg 2>/dev/null | /usr/bin/tail -40
        /usr/sbin/iptables -w 5 -S INPUT 2>/dev/null
    } > "$DIAG" 2>&1
    echo "no listener on :$PORT" > "$FAILED"
    echo "FAILED: no listener on :$PORT"
    exit 1
fi
