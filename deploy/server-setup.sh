#!/usr/bin/env bash
# Run ON the server with sudo (deploy.sh does this for you).
# Installs the site as its OWN small service on its OWN port. It does not install packages,
# does not touch nginx/apache/docker or any existing port, file or firewall rule.
set -euo pipefail
PORT="${PORT:-8088}"
NAME=crack-readout
SRC=/tmp/crack-readout-deploy
DEST=/opt/$NAME
SVC_USER=crackreadout

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "python3 not found. Install it first; this script installs nothing."; exit 1; }
[ -d "$SRC/site" ] || { echo "Missing $SRC/site. Run deploy.sh from your computer."; exit 1; }

# Re-runs: stop our own service first so its port counts as free.
systemctl stop "$NAME" 2>/dev/null || true
if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${PORT}$"; then
  echo "Port $PORT is already used by something else. Nothing was changed."
  echo "Choose another port, for example:  PORT=8099 bash deploy/deploy.sh user@ip key"
  exit 2
fi

id -u "$SVC_USER" >/dev/null 2>&1 || useradd --system --no-create-home --shell "$(command -v nologin || echo /bin/false)" "$SVC_USER"

mkdir -p "$DEST"
rm -rf "${DEST:?}"/*
cp -r "$SRC"/site/. "$DEST"/
chown -R root:root "$DEST"
chmod -R a+rX "$DEST"

cat > /etc/systemd/system/$NAME.service <<UNIT
[Unit]
Description=Crack Signal Readout (static site)
After=network.target

[Service]
User=$SVC_USER
ExecStart=$PY -m http.server $PORT --bind 0.0.0.0 --directory $DEST
Restart=on-failure
MemoryMax=64M
CPUQuota=15%
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

# Open ONLY this port in the host firewall, whichever one is active.
if command -v firewall-cmd >/dev/null && firewall-cmd --state >/dev/null 2>&1; then
  firewall-cmd --permanent --add-port="${PORT}/tcp" >/dev/null && firewall-cmd --reload >/dev/null
elif command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow "${PORT}/tcp"
elif command -v iptables >/dev/null; then
  iptables -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport "$PORT" -j ACCEPT
  command -v netfilter-persistent >/dev/null && netfilter-persistent save >/dev/null 2>&1 || true
fi

systemctl daemon-reload
systemctl enable --now "$NAME"
sleep 1
echo "Local check:"; curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://127.0.0.1:${PORT}/"
echo "Service:"; systemctl is-active "$NAME"
echo "Done. Now open port $PORT in the Oracle console (see deploy/README.md, step 2)."
