#!/bin/sh
# Install the persistent Titan OS root hook.
#
# Run this as root on the TV, for example from the USB autoroot telnet shell.
# It writes /mtd_rwarea/apdat/root_boot.sh, persists the known-good busybox,
# and installs the boot hook that this firmware actually reads:
#
#   customer_env.sh variant
#     /mtd_apexe/board/run.sh sources /mtd_apdat/customer_env.sh. Append one
#     line there. This is the documented path for the verified target.
#
#   /swdl/telnet/telnetd variant
#     Some later TPN256E firmware no longer sources customer_env.sh, but its
#     run_custom_impl.sh still executes /swdl/telnet/telnetd if the file is
#     executable. Write a one-line wrapper there instead. Reported by Pedram
#     on TPN256E_V056.010.032.001; see docs/research/24.
#
# Nothing in the read-only rootfs, boot chain, or raw flash images is modified.
# The only writes are to the writable apdat filesystem and, on the /swdl
# variant, the writable /swdl filesystem.
#
# Restore (run the lines for the variant the installer selected):
#   sed -i '/root_boot.sh/d' /mtd_rwarea/apdat/customer_env.sh
#   rm -f /swdl/telnet/telnetd
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
RUN_SH=/mtd_apexe/board/run.sh
RUN_CUSTOM_IMPL=/mtd_apexe/board/run_custom_impl.sh
SWDL_TELNET=/swdl/telnet/telnetd

[ "$(id -u)" = "0" ] || { echo "ERROR: must run as root"; exit 1; }
[ -d "$BASE" ] || { echo "ERROR: $BASE is missing"; exit 1; }
[ -w "$BASE" ] || { echo "ERROR: $BASE is not writable"; exit 1; }
[ -f "$BUSYBOX_SRC" ] || {
    echo "ERROR: missing $BUSYBOX_SRC"
    echo "Run this from the USB autoroot shell, where /tmp/busybox is the running binary."
    exit 1
}

# Choose the hook from the live firmware. Do not append to customer_env.sh on a
# build that no longer sources it: the file would look installed but never run.
if [ -f "$RUN_SH" ] && grep -Eq '^[[:space:]]*(source|\.)[[:space:]]+.*customer_env\.sh' "$RUN_SH"; then
    HOOK=customer_env
elif [ -f "$RUN_CUSTOM_IMPL" ] && grep -q '/swdl/telnet/telnetd' "$RUN_CUSTOM_IMPL"; then
    HOOK=swdl
else
    echo "ERROR: no known boot hook found." >&2
    echo "Diagnose with:" >&2
    echo "  grep -n customer_env $RUN_SH" >&2
    echo "  grep -n /swdl/telnet $RUN_CUSTOM_IMPL" >&2
    echo "Nothing was written. Report both outputs with your firmware version." >&2
    exit 1
fi

echo "Installing persistent root hook in $BASE ($HOOK variant)"

cp "$BUSYBOX_SRC" "$BASE/busybox" || exit 1
chmod 0755 "$BASE/busybox" || exit 1

cat > "$BASE/root_boot.sh" <<'ROOTBOOT'
#!/bin/sh
# Titan OS persistent root hook.
#
# The selected boot hook (customer_env.sh or /swdl/telnet/telnetd) starts this
# script in the background early in boot, before iptables_conf.sh. Wait for the
# boot to pass quick_debug/menu's own driver marker and for the boot firewall
# to settle, then open one port and start busybox telnetd from tmpfs.
#
# Nothing is written outside /mtd_rwarea/apdat and /tmp. Remove the selected
# boot hook to restore normal boot.

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

case "$HOOK" in
customer_env)
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
    ;;
swdl)
    [ -d /swdl ] || { echo "ERROR: /swdl is missing"; exit 1; }
    [ -w /swdl ] || { echo "ERROR: /swdl is not writable"; exit 1; }
    mkdir -p /swdl/telnet || exit 1

    # A vendor file may already live here. Keep it, but do not silently lose it.
    if [ -f "$SWDL_TELNET" ] && ! grep -q 'root_boot.sh' "$SWDL_TELNET" 2>/dev/null; then
        cp -a "$SWDL_TELNET" "$SWDL_TELNET.bak" 2>/dev/null || true
    fi

    # run_custom_impl.sh executes this early in boot, before iptables_conf.sh.
    # Background the delayed root_boot.sh and return.
    cat > "$SWDL_TELNET" <<'SWDLHOOK' || exit 1
#!/bin/sh
# Vendor run_custom_impl.sh executes this early in boot, before
# iptables_conf.sh. Background the delayed root_boot.sh and return.
[ -f /mtd_rwarea/apdat/root_boot.sh ] && /bin/sh /mtd_rwarea/apdat/root_boot.sh &
SWDLHOOK
    chmod 0755 "$SWDL_TELNET" || exit 1

    # Do not restorecon this file. The variant report verified the inherited
    # /swdl label as-is; apdat's idtv_data_t policy does not apply here.
    ;;
esac

echo
echo "Installed:"
ls -l "$BASE/busybox" "$BASE/root_boot.sh"
if [ "$HOOK" = customer_env ]; then
    ls -l "$BASE/customer_env.sh"
    echo
    echo "customer_env.sh:"
    cat "$BASE/customer_env.sh"
else
    ls -l "$SWDL_TELNET"
    echo
    echo "Boot hook:"
    cat "$SWDL_TELNET"
fi
echo
echo "Test now:"
echo "  /bin/sh $BASE/root_boot.sh"
echo "  cat $BASE/root_boot.log"
echo "  cat $BASE/root_boot.ready"
echo
if [ "$HOOK" = customer_env ]; then
    echo "Restore the hook with:"
    echo "  sed -i '/root_boot.sh/d' $BASE/customer_env.sh"
else
    echo "Restore the hook with:"
    echo "  rm -f $SWDL_TELNET"
    echo "  # If $SWDL_TELNET.bak exists, inspect it first; the installer"
    echo "  # only creates it when a pre-existing file was present."
fi
echo
echo "Then remove the USB, cold boot, wait ~20 s, and reconnect to :2323."
