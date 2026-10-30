#!/usr/bin/env bash
# Run ON the server with sudo. Removes ONLY what server-setup.sh created.
set -u
PORT="${PORT:-8088}"; NAME=crack-readout
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
systemctl disable --now "$NAME" 2>/dev/null
rm -f /etc/systemd/system/$NAME.service && systemctl daemon-reload
rm -rf /opt/$NAME /tmp/crack-readout-deploy
id -u crackreadout >/dev/null 2>&1 && userdel crackreadout
if command -v firewall-cmd >/dev/null && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --permanent --remove-port="${PORT}/tcp" >/dev/null; firewall-cmd --reload >/dev/null
elif command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw delete allow "${PORT}/tcp"
elif command -v iptables >/dev/null; then
  iptables -D INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null
  command -v netfilter-persistent >/dev/null && netfilter-persistent save >/dev/null 2>&1
fi
echo "Removed. Your other projects were never touched."
