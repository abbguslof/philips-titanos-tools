#!/bin/sh
# Install the persistent Titan OS root hook.
#
# Run this as root on the TV, for example from the USB autoroot telnet shell.
# It writes /mtd_rwarea/apdat/root_boot.sh, persists the known-good busybox,
# and hooks the script from /mtd_rwarea/apdat/customer_env.sh, which
# /mtd_apexe/board/run.sh sources as root on every boot.
#
# Nothing in the read-only rootfs or flash partitions is modified.
#
# Restore:
#   sed -i '/root_boot.sh/d' /mtd_rwarea/apdat/customer_env.sh
#   rm -f /mtd_rwarea/apdat/root_boot.sh /mtd_rwarea/apdat/busybox \
#         /mtd_rwarea/apdat/root_boot.log /mtd_rwarea/apdat/root_boot.ready \
#         /mtd_rwarea/apdat/root_boot.ready.failed
#   cold boot
#
# The USB autoroot stick remains the recovery path if this hook is removed or
# stops working.

set -u

BASE=/mtd_rwarea/apdat
BUSYBOX_SRC=${BUSYBOX_SRC:-/tmp/busybox}

[ "$(id -u)" = "0" ] || { echo "ERROR: must run as root"; exit 1; }
[ -d "$BASE" ] || { echo "ERROR: $BASE is missing"; exit 1; }
[ -w "$BASE" ] || { echo "ERROR: $BASE is not writable"; exit 1; }
[ -f "$BUSYBOX_SRC" ] || {
    echo "ERROR: missing $BUSYBOX_SRC"
    echo "Run this from the USB autoroot shell, where /tmp/busybox is the running binary."
    exit 1
}

echo "Installing persistent root hook in $BASE"

cp "$BUSYBOX_SRC" "$BASE/busybox" || exit 1
chmod 0755 "$BASE/busybox" || exit 1

cat > "$BASE/root_boot.sh" <<'ROOTBOOT'
#!/bin/sh
# Titan OS persistent root hook.
#
# customer_env.sh is sourced by /mtd_apexe/board/run.sh early in boot, before
# iptables_conf.sh. Start this script in the background, wait for the boot to
# pass quick_debug/menu's own driver marker and for the boot firewall to settle,
# then open one port and start busybox telnetd from tmpfs.
#
# Nothing is written outside /mtd_rwarea/apdat and /tmp. Remove the hook from
# customer_env.sh to restore normal boot.

PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH

BASE=/mtd_rwarea/apdat
LOG=$BASE/root_boot.log
READY=$BASE/root_boot.ready
FAILED=$BASE/root_boot.ready.failed
PORT=2323
RUNTIME=/tmp/persist/busybox

exec >>"$LOG" 2>&1

echo "=== root_boot start ==="
echo "date: $(date 2>/dev/null)"
echo "uptime: $(cat /proc/uptime 2>/dev/null)"
id

rm -f "$READY" "$FAILED"

die() {
    echo "FATAL: $*"
    echo "$*" > "$FAILED"
    exit 1
}

# run.sh sources customer_env.sh before iptables_conf.sh flushes INPUT. The
# marker used by quick_debug/menu appears after driver init; add a fixed safety
# delay after it so the boot firewall has finished.
n=0
while [ ! -f /tmp/ntkdriver_completed ] && [ "$n" -lt 60 ]; do
    sleep 1
    n=$((n + 1))
done
[ -f /tmp/ntkdriver_completed ] || sleep 15
sleep 5

[ -f "$BASE/busybox" ] || die "missing $BASE/busybox"
/bin/mkdir -p /tmp/persist
/bin/cp "$BASE/busybox" "$RUNTIME" || die "copy busybox failed"
/bin/chmod 0755 "$RUNTIME" || die "chmod busybox failed"
"$RUNTIME" --list 2>/dev/null | /bin/grep -qx telnetd || die "busybox has no telnetd applet"

# Insert only if the exact rule is not already present. -w waits for the
# xtables lock held by the DLNA, update, and telemetry daemons during boot.
if [ -x /usr/sbin/iptables ]; then
    /usr/sbin/iptables -w 5 -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null \
        || /usr/sbin/iptables -w 5 -I INPUT 1 -p tcp --dport "$PORT" -j ACCEPT \
        || echo "WARN: iptables rule failed"
else
    echo "WARN: /usr/sbin/iptables missing"
fi
if [ -x /usr/sbin/ip6tables ]; then
    /usr/sbin/ip6tables -w 5 -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null \
        || /usr/sbin/ip6tables -w 5 -I INPUT 1 -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null \
        || echo "WARN: ip6tables rule failed"
fi

# Do not use pkill. If this runs twice, the second pass must not kill the
# listener the first pass created.
if /bin/netstat -ltn 2>/dev/null | /bin/grep -qE "[:.]$PORT[[:space:]]"; then
    echo "port $PORT already listening"
else
    "$RUNTIME" telnetd -p "$PORT" -l /bin/sh &
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
    echo "READY $(date 2>/dev/null) uptime=$(cat /proc/uptime 2>/dev/null)" > "$READY"
    echo "SUCCESS: telnetd listening on :$PORT"
    /usr/sbin/iptables -w 5 -S INPUT 2>/dev/null
else
    echo "FAILED: no listener on :$PORT"
    /bin/netstat -ltn
    /bin/ps w
    /bin/dmesg 2>/dev/null | /usr/bin/tail -40
    echo "no listener on :$PORT" > "$FAILED"
    exit 1
fi
ROOTBOOT
chmod 0755 "$BASE/root_boot.sh" || exit 1

# Preserve any existing customer environment file before touching it.
if [ -f "$BASE/customer_env.sh" ]; then
    cp -a "$BASE/customer_env.sh" "$BASE/customer_env.sh.bak" 2>/dev/null || true
fi

# Do not add the hook twice.
if ! grep -q 'root_boot.sh' "$BASE/customer_env.sh" 2>/dev/null; then
    printf '\n[ -f /mtd_rwarea/apdat/root_boot.sh ] && /bin/sh /mtd_rwarea/apdat/root_boot.sh &\n' >> "$BASE/customer_env.sh"
fi

# Keep the SELinux labels in line with /mtd_rwarea/apdat (idtv_data_t).
if command -v restorecon >/dev/null 2>&1; then
    restorecon "$BASE/busybox" "$BASE/root_boot.sh" "$BASE/customer_env.sh" 2>/dev/null || true
fi

echo
echo "Installed:"
ls -l "$BASE/busybox" "$BASE/root_boot.sh" "$BASE/customer_env.sh"
echo
echo "customer_env.sh:"
cat "$BASE/customer_env.sh"
echo
echo "Test now:"
echo "  /bin/sh $BASE/root_boot.sh"
echo "  cat $BASE/root_boot.log"
echo "  cat $BASE/root_boot.ready"
echo
echo "Then remove the USB, cold boot, wait ~20 s, and reconnect to :2323."
