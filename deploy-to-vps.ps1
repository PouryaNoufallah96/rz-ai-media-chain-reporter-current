#!/usr/bin/env pwsh
# ChainReporter VPS Deployment Script

param(
    [string]$VpsIP = "5.75.207.209",
    [string]$VpsUser = "root",
    [string]$SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519",
    [string]$ProjectRoot = "c:\Users\Nikan Computer\ChainR-June-02"
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ChainReporter VPS Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  VPS IP:       $VpsIP"
Write-Host "  User:         $VpsUser"
Write-Host "  SSH Key:      $SshKeyPath"
Write-Host "  Project Root: $ProjectRoot"
Write-Host ""

if (-not (Test-Path $SshKeyPath)) {
    Write-Host "ERROR: SSH key not found" -ForegroundColor Red
    exit 1
}

$SshOpts = @("-i", $SshKeyPath, "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null")

# Test SSH connection
Write-Host "Testing SSH connection..." -ForegroundColor Cyan
$output = ssh $SshOpts "${VpsUser}@${VpsIP}" "echo OK"
if ($output -ne "OK") {
    Write-Host "ERROR: SSH connection failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] SSH connection successful" -ForegroundColor Green
Write-Host ""

# Upload backend
Write-Host "Uploading backend files..." -ForegroundColor Cyan
scp -r @SshOpts "$ProjectRoot\backend" "${VpsUser}@${VpsIP}:/var/www/chainreporter/" 2>&1 | Select-Object -Last 3
Write-Host "[OK] Backend uploaded" -ForegroundColor Green
Write-Host ""

# Upload frontend
Write-Host "Uploading frontend dist..." -ForegroundColor Cyan
scp -r @SshOpts "$ProjectRoot\frontend\dist" "${VpsUser}@${VpsIP}:/var/www/chainreporter/frontend/" 2>&1 | Select-Object -Last 3
Write-Host "[OK] Frontend uploaded" -ForegroundColor Green
Write-Host ""

# Upload service files
Write-Host "Uploading service files..." -ForegroundColor Cyan
scp @SshOpts "$ProjectRoot\deploy\chainreporter-backend.service" "${VpsUser}@${VpsIP}:/tmp/"
scp @SshOpts "$ProjectRoot\deploy\chainreporter-frontend.service" "${VpsUser}@${VpsIP}:/tmp/"
Write-Host "[OK] Service files uploaded" -ForegroundColor Green
Write-Host ""

# Remote installation
Write-Host "Installing dependencies and restarting..." -ForegroundColor Cyan
ssh @SshOpts "${VpsUser}@${VpsIP}" @"
set -e
cd /var/www/chainreporter/backend
pip3 install -r requirements.txt --quiet
cp /tmp/chainreporter-backend.service /etc/systemd/system/
cp /tmp/chainreporter-frontend.service /etc/systemd/system/
systemctl daemon-reload
chown -R www-data:www-data /var/www/chainreporter
systemctl restart chainreporter-backend chainreporter-frontend
sleep 3
echo "Services restarted successfully"
"@

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access the app:" -ForegroundColor Cyan
Write-Host "  Frontend: http://5.75.207.209:3000"
Write-Host "  Backend:  http://5.75.207.209:3001"
Write-Host ""
Write-Host "Check service status:" -ForegroundColor Cyan
Write-Host "  ssh -i $SshKeyPath root@5.75.207.209 systemctl status chainreporter-backend"
Write-Host ""
