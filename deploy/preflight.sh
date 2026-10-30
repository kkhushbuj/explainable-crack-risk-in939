#!/usr/bin/env bash
# READ-ONLY. Changes nothing. Run it on the server to see what is already running there.
set -u
echo "== OS =="; (. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME")
echo "== Memory (MB) =="; free -m | sed -n 1,2p
echo "== Disk =="; df -h / | tail -1
echo "== Listening TCP ports (these belong to your other projects) =="
(ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null) | head -40
echo "== Web servers =="
for s in nginx apache2 httpd caddy; do printf "%s: " "$s"; systemctl is-active "$s" 2>/dev/null || echo "not installed"; done
echo "== Docker containers =="
if command -v docker >/dev/null; then docker ps --format '{{.Names}}  {{.Ports}}' 2>/dev/null || echo "(docker needs sudo)"; else echo "docker not installed"; fi
echo "== Firewall =="
if command -v firewall-cmd >/dev/null; then firewall-cmd --state 2>/dev/null; firewall-cmd --list-ports 2>/dev/null; else echo "no firewalld"; fi
if command -v iptables >/dev/null; then sudo -n iptables -S INPUT 2>/dev/null | head -15 || echo "(iptables needs sudo)"; fi
echo "== Python =="; python3 --version 2>&1
echo "== Is the planned port (8088) free? =="
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq '[:.]8088$'; then echo "8088 is IN USE"; else echo "8088 is free"; fi
