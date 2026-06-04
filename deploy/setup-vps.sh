#!/bin/bash
# ChainReporter VPS setup script
# Debian 11/12, IP 5.75.207.209, Hetzner Falkenstein
# Run as root: bash setup-vps.sh

set -e

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
mkdir -p /var/www/chainreporter
chown -R www-data:www-data /var/www/chainreporter

echo "=== 6. Copy systemd units ==="
cp chainreporter-backend.service  /etc/systemd/system/
cp chainreporter-frontend.service /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== NEXT STEPS (run after deploying files) ==="
echo "1. cd /var/www/chainreporter/backend"
echo "2. pip3 install -r requirements.txt"
echo "3. Create /var/www/chainreporter/backend/.env with your API keys"
echo "   (set FRONTEND_ORIGIN=http://5.75.207.209:3000)"
echo "4. chown -R www-data:www-data /var/www/chainreporter"
echo "5. systemctl enable --now chainreporter-backend chainreporter-frontend"
echo "6. Test: curl http://5.75.207.209:3001/api/health"
echo "7. Open browser: http://5.75.207.209:3000"
