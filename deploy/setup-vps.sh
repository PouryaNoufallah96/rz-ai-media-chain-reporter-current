#!/bin/bash
# ChainReporter VPS setup script
# Debian 11, IP 5.75.207.209, Hetzner Falkenstein
# Run as root: bash setup-vps.sh

set -e

echo "=== 1. System update ==="
apt-get update && apt-get upgrade -y

echo "=== 2. Install Python 3.10+ ==="
apt-get install -y python3.10 python3.10-venv python3.10-distutils python3-pip

echo "=== 3. Install Node.js 18+ ==="
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

echo "=== 4. Install Puppeteer Chrome dependencies ==="
apt-get install -y \
  libnss3 libxss1 libgconf-2-4 libappindicator1 \
  fonts-liberation xdg-utils libxkbcommon0 libx11-xcb1 \
  libatk-bridge2.0-0 libgtk-3-0 libasound2

echo "=== 5. Open firewall ports ==="
ufw allow 22/tcp
ufw allow 3000/tcp
ufw allow 3001/tcp
ufw --force enable
ufw status

echo "=== 6. Create app directory ==="
mkdir -p /var/www/chainreporter
chown -R www-data:www-data /var/www/chainreporter

echo "=== 7. Copy systemd units ==="
cp chainreporter-backend.service  /etc/systemd/system/
cp chainreporter-frontend.service /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== NEXT STEPS ==="
echo "1. Copy your project files to /var/www/chainreporter/"
echo "2. Copy backend/.env to /var/www/chainreporter/backend/.env"
echo "3. Set FRONTEND_ORIGIN=http://5.75.207.209:3000 in the .env"
echo "4. cd /var/www/chainreporter/backend && pip3 install -r requirements.txt"
echo "5. cd /var/www/chainreporter && npm install"
echo "6. systemctl enable --now chainreporter-backend chainreporter-frontend"
echo "7. Test: curl http://5.75.207.209:3001/api/health"
echo "8. Open browser: http://5.75.207.209:3000"
