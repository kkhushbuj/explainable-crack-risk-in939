#!/usr/bin/env bash
# Run on YOUR computer, from the repo folder:  bash deploy/deploy.sh ubuntu@SERVER_IP /path/to/your-private-key
set -euo pipefail
[ $# -eq 2 ] || { echo "Usage: bash deploy/deploy.sh user@server-ip /path/to/ssh-private-key"; exit 1; }
TARGET="$1"; KEY="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"

python3 "$HERE/build_site.py"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
$SSH "$TARGET" "rm -rf /tmp/crack-readout-deploy && mkdir -p /tmp/crack-readout-deploy"
scp -i "$KEY" -r "$HERE/site" "$HERE/nginx-crack-readout.conf" "$HERE/server-setup.sh" "$TARGET:/tmp/crack-readout-deploy/"
$SSH -t "$TARGET" "sudo bash /tmp/crack-readout-deploy/server-setup.sh"
echo "Open: http://${TARGET#*@}/"
