# Block for /mtd_rwarea/apdat/root_boot.sh: install prefix and SSH.
# Insert after the driver-marker wait and the 5 s firewall delay, before the
# busybox copy. Verified on 2026-11-10 with the USB removed:
# docs/research/23-dropbear-ssh-2026-11-10.md
#
# --- /mtd_rwarea/apdat/opt: tools + ssh ---
OPT="$BASE/opt"
if ! /bin/grep -q " /root tmpfs " /proc/mounts; then
    /bin/mount -t tmpfs -o mode=700,size=1m tmpfs /root 2>/dev/null
fi
if [ -f "$OPT/root_home/.ssh/authorized_keys" ]; then
    /bin/mkdir -p /root/.ssh 2>/dev/null
    /bin/cp -f "$OPT/root_home/.ssh/authorized_keys" /root/.ssh/authorized_keys 2>/dev/null
    /bin/chmod 700 /root /root/.ssh 2>/dev/null
    /bin/chmod 600 /root/.ssh/authorized_keys 2>/dev/null
fi
if [ -d /etc/profile.d ] && ! /bin/grep -q " /etc/profile.d " /proc/mounts; then
    /bin/mkdir -p "$OPT/etc/profile.d" 2>/dev/null
    /bin/cp -f /etc/profile.d/*.sh "$OPT/etc/profile.d/" 2>/dev/null
    /bin/echo "export PATH=\"\$PATH:$OPT/bin\"" > "$OPT/etc/profile.d/opt-bin.sh"
    /bin/chmod 644 "$OPT/etc/profile.d/opt-bin.sh" 2>/dev/null
    /bin/mount --bind "$OPT/etc/profile.d" /etc/profile.d 2>/dev/null
fi
if [ -x /usr/sbin/iptables ]; then
    /usr/sbin/iptables -w 5 -C INPUT -p tcp --dport 2222 -j ACCEPT 2>/dev/null \
        || /usr/sbin/iptables -w 5 -I INPUT 1 -p tcp --dport 2222 -j ACCEPT \
        || echo "WARN: ssh iptables rule failed"
fi
if [ -x /usr/sbin/ip6tables ]; then
    /usr/sbin/ip6tables -w 5 -C INPUT -p tcp --dport 2222 -j ACCEPT 2>/dev/null \
        || /usr/sbin/ip6tables -w 5 -I INPUT 1 -p tcp --dport 2222 -j ACCEPT 2>/dev/null
fi
/bin/chmod 755 "$OPT/etc/profile.d" 2>/dev/null
/bin/chmod 644 "$OPT/etc/profile.d/"*.sh 2>/dev/null
/bin/chmod 600 "$OPT/etc/dropbear/ed25519_host_key" 2>/dev/null
if [ -x "$OPT/bin/dropbearmulti" ] && [ ! -f "$OPT/disabled" ]; then
    if /bin/netstat -ltn 2>/dev/null | /bin/grep -qE "[:.]2222[[:space:]]"; then
        echo "ssh port 2222 already listening"
    else
        "$OPT/bin/dropbearmulti" dropbear -F -p 2222 \
            -r "$OPT/etc/dropbear/ed25519_host_key" -s \
            </dev/null >>"$OPT/var/dropbear.log" 2>&1 &
        echo "dropbear pid $!"
    fi
fi
