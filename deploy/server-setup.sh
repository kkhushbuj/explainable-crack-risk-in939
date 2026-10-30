#!/usr/bin/env bash
# Run ON the Oracle VM (Ubuntu) with sudo. deploy.sh does this for you.
set -euo pipefail
SRC=/tmp/crack-readout-deploy
WEB=/var/www/crack-readout

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

apt-get update -y
apt-get install -y nginx

# Do not disturb other sites that may already live on this server.
others=$(ls /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null | grep -v -E '^(default|crack-readout\.conf|)$' || true)
if [ -n "$others" ]; then
  echo "Other nginx sites found:"; echo "$others"
  echo "Stopping so nothing existing is changed. Tell Claude what is on this server first."
  exit 2
fi
rm -f /etc/nginx/sites-enabled/default

mkdir -p "$WEB"
rm -rf "${WEB:?}"/*
cp -r "$SRC"/site/. "$WEB"/
chown -R www-data:www-data "$WEB"
cp "$SRC/nginx-crack-readout.conf" /etc/nginx/conf.d/crack-readout.conf

# Oracle Ubuntu images block port 80 in iptables by default.
if command -v iptables >/dev/null && ! iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; then
  iptables -I INPUT -m state --state NEW -p tcp --dport 80 -j ACCEPT
  command -v netfilter-persistent >/dev/null && netfilter-persistent save || true
fi
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw allow 80/tcp; fi

nginx -t
systemctl enable nginx
systemctl reload nginx || systemctl restart nginx
echo "Local check:"; curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1/
echo "Done. Also open port 80 in the Oracle console (see deploy/README.md, step 3)."
