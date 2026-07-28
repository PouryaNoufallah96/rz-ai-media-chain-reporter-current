#!/bin/bash
# ChainReporter VPS setup script
# Debian 11/12, IP 5.75.207.209, Hetzner Falkenstein
# Run as root: bash setup-vps.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_FILE="$PROJECT_ROOT/DEPLOYMENT_TARGET.lock"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

read_lock_value() {
  local key="$1"
  grep -E "^${key}=" "$LOCK_FILE" | head -n 1 | cut -d= -f2-
}

[ -f "$LOCK_FILE" ] || die "Deployment lock not found: $LOCK_FILE"

PROJECT_ID="$(read_lock_value project_id)"
PROJECT_NAME="$(read_lock_value project_name)"
VPS_IP="$(read_lock_value vps_ip)"
REMOTE_ROOT="$(read_lock_value remote_root)"
BACKEND_SERVICE="$(read_lock_value backend_service)"
FRONTEND_SERVICE="$(read_lock_value frontend_service)"
FORBID_VPS_IP="$(read_lock_value forbid_vps_ip)"
FORBID_REMOTE_ROOT="$(read_lock_value forbid_remote_root)"

[ "$PROJECT_ID" = "chainreporter" ] || die "project_id must be chainreporter, got $PROJECT_ID"
[ "$PROJECT_NAME" = "ChainReporter" ] || die "project_name must be ChainReporter, got $PROJECT_NAME"
[ "$VPS_IP" = "5.75.207.209" ] || die "VPS IP must be 5.75.207.209, got $VPS_IP"
[ "$REMOTE_ROOT" = "/var/www/chainreporter" ] || die "remote_root must be /var/www/chainreporter, got $REMOTE_ROOT"
[ "$VPS_IP" != "$FORBID_VPS_IP" ] || die "Refusing forbidden VPS: $VPS_IP"
[ "$REMOTE_ROOT" != "$FORBID_REMOTE_ROOT" ] || die "Refusing forbidden remote root: $REMOTE_ROOT"
[ "$BACKEND_SERVICE" = "chainreporter-backend" ] || die "backend_service must be chainreporter-backend, got $BACKEND_SERVICE"
[ "$FRONTEND_SERVICE" = "chainreporter-frontend" ] || die "frontend_service must be chainreporter-frontend, got $FRONTEND_SERVICE"

echo "=== 1. System update ==="
apt-get update && apt-get upgrade -y

echo "=== 2. Install Python 3 + pip ==="
apt-get install -y python3 python3-venv python3-pip

echo "=== 3. Install Node.js 18+ ==="
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

echo "=== 4. Open firewall ports ==="
ufw allow 22/tcp
ufw allow 3000/tcp
ufw allow 3001/tcp
ufw --force enable
ufw status

echo "=== 5. Create app directory ==="
mkdir -p "$REMOTE_ROOT"
chown -R www-data:www-data "$REMOTE_ROOT"

echo "=== 6. Copy systemd units ==="
cp "${BACKEND_SERVICE}.service"  /etc/systemd/system/
cp "${FRONTEND_SERVICE}.service" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== NEXT STEPS (run after deploying files) ==="
echo "1. cd $REMOTE_ROOT/backend"
echo "2. pip3 install -r requirements.txt"
echo "3. Create $REMOTE_ROOT/backend/.env with your API keys"
echo "   (set FRONTEND_ORIGIN=http://$VPS_IP)"
echo "4. chown -R www-data:www-data $REMOTE_ROOT"
echo "5. systemctl enable --now $BACKEND_SERVICE $FRONTEND_SERVICE"
echo "6. Test: curl http://$VPS_IP/api/health"
echo "7. Open browser: http://$VPS_IP/login"
