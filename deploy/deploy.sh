#!/usr/bin/env bash
# Run on YOUR computer, from the repo folder:
#   bash deploy/deploy.sh ubuntu@SERVER_IP /path/to/your-private-key [port]
set -euo pipefail
[ $# -ge 2 ] || { echo "Usage: bash deploy/deploy.sh user@server-ip /path/to/ssh-private-key [port]"; exit 1; }
TARGET="$1"; KEY="$2"; PORT="${3:-8088}"; HERE="$(cd "$(dirname "$0")" && pwd)"

python3 "$HERE/build_site.py"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
$SSH "$TARGET" "rm -rf /tmp/crack-readout-deploy && mkdir -p /tmp/crack-readout-deploy"
scp -i "$KEY" -r "$HERE/site" "$HERE/server-setup.sh" "$TARGET:/tmp/crack-readout-deploy/"
$SSH -t "$TARGET" "sudo PORT=$PORT bash /tmp/crack-readout-deploy/server-setup.sh"
echo "Open: http://${TARGET#*@}:${PORT}/"
