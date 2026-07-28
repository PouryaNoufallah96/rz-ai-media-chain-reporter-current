#!/usr/bin/env pwsh
# ============================================================================
# ChainReporter VPS Deploy -- per-file workflow (matches the manual scp method)
# ============================================================================
# Deploys ONLY the files that changed (auto-detected via git), uploads each one
# to the VPS, syntax-checks the backend, rebuilds the frontend ON the VPS, and
# restarts the affected services. Never touches backend/data/ (the SQLite DB),
# .env, or caches -- so the production database and secrets are always safe.
#
# Usage (run from anywhere; defaults point at the project root + your VPS):
#   .\deploy-to-vps.ps1                  # deploy all changed files vs HEAD
#   .\deploy-to-vps.ps1 -DryRun          # show what would deploy, upload nothing
#   .\deploy-to-vps.ps1 -Files "backend/config.py,frontend/src/pages/AccountPage.jsx"
#   .\deploy-to-vps.ps1 -SkipRestart     # upload + build only, don't restart
#   .\deploy-to-vps.ps1 -SshKeyPath ".\.deploy_chainreporter_vps_key"
#
# What gets deployed:
#   backend/*           -> /var/www/chainreporter/backend/*
#   frontend/src/*      -> /var/www/chainreporter/frontend/src/*   (then built on VPS)
# Everything else is ignored. backend/data/, backend/.env, __pycache__ are excluded.
#
# SSH key lookup:
#   1. Explicit -SshKeyPath value, if provided.
#   2. .\.deploy_chainreporter_vps_key in the project root, if present.
#   3. $env:USERPROFILE\.ssh\id_ed25519.
# The chosen key is copied/canonicalized to a temp file readable only by the
# current process user. This matters in Codex, where Windows may run commands as
# CodexSandboxOffline while $env:USERNAME still points at the desktop user.
# ============================================================================

param(
    [string]$VpsIP      = "5.75.207.209",
    [string]$VpsUser    = "root",
    [string]$SshKeyPath = "",
    [string]$ProjectRoot = "c:\Users\Nikan Computer\ChainR-June-02",
    [string]$Since      = "HEAD",          # git ref to diff against (ignored if -Files set)
    [string]$Files      = "",              # comma-sep explicit list (overrides auto-detect)
    [switch]$DryRun,
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"

# PS 5.1 turns native-command stderr (git CRLF warnings, ssh "Permanently added"
# notices, npm deprecation banners) into NativeCommandError records that -- with
# the Stop preference above -- would abort the script. We drive every ssh/scp/git
# call by checking $LASTEXITCODE explicitly, so we don't want stderr to be fatal.
# "Continue" lets those harmless stderr lines print without crashing us.
$global:ErrorActionPreference = "Continue"
# Keep our helpers able to exit on real failures via explicit checks, not EAP.
function Step($m) { Write-Host "`n>>> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    [OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    [!!] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "    ERROR: $m" -ForegroundColor Red; exit 1 }

Set-Location $ProjectRoot | Out-Null

if (-not $SshKeyPath) {
    $WorkspaceKeyPath = Join-Path $ProjectRoot ".deploy_chainreporter_vps_key"
    if (Test-Path $WorkspaceKeyPath) {
        $SshKeyPath = $WorkspaceKeyPath
    } else {
        $SshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519"
    }
}

function Get-CurrentWindowsUser {
    $u = (whoami 2>$null)
    if ($LASTEXITCODE -eq 0 -and $u) { return ($u | Select-Object -First 1).Trim() }
    return "$($env:COMPUTERNAME)\$($env:USERNAME)"
}

function Find-BundledPython {
    $candidates = @(
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
        "C:\Users\Nikan Computer\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return ""
}

function Prepare-SshKeyForCurrentUser($sourcePath) {
    try {
        if (-not (Test-Path $sourcePath)) { Die "SSH key not found or not readable: $sourcePath" }
    } catch {
        Die "SSH key not readable from this process: $sourcePath. Put a readable key at .\.deploy_chainreporter_vps_key."
    }

    $currentUser = Get-CurrentWindowsUser
    $prepared = Join-Path $env:TEMP ("chainreporter_deploy_key_" + $PID)
    $py = Find-BundledPython

    $canonicalized = $false
    if ($py) {
        $code = @"
import sys
from pathlib import Path
src, dst = sys.argv[1], sys.argv[2]
data = Path(src).read_bytes()
try:
    from cryptography.hazmat.primitives import serialization
    key = serialization.load_ssh_private_key(data, password=None)
    data = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    )
except Exception:
    pass
Path(dst).write_bytes(data)
"@
        & $py -c $code $sourcePath $prepared | Out-Null
        if ($LASTEXITCODE -eq 0 -and (Test-Path $prepared)) { $canonicalized = $true }
    }

    if (-not $canonicalized) {
        Copy-Item -LiteralPath $sourcePath -Destination $prepared -Force
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $prepared)) { Die "Failed to prepare SSH key copy." }
    }

    icacls $prepared /inheritance:r | Out-Null
    icacls $prepared /grant:r "${currentUser}:(R)" | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "Failed to lock down prepared SSH key for $currentUser" }

    return $prepared
}

function Read-DeploymentLock($path) {
    if (-not (Test-Path $path)) { Die "Deployment lock not found: $path" }

    $lock = @{}
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) { Die "Invalid deployment lock line: $line" }
        $lock[$parts[0].Trim()] = $parts[1].Trim()
    }

    foreach ($key in @("project_id", "project_name", "vps_ip", "remote_root", "backend_service", "frontend_service", "forbid_vps_ip", "forbid_remote_root")) {
        if (-not $lock.ContainsKey($key) -or -not $lock[$key]) { Die "Deployment lock missing required key: $key" }
    }

    return $lock
}

function Assert-DeploymentTarget($lock) {
    if ($lock.project_id -ne "chainreporter") { Die "Local deployment lock project_id must be chainreporter, got $($lock.project_id)" }
    if ($lock.project_name -ne "ChainReporter") { Die "Local deployment lock project_name must be ChainReporter, got $($lock.project_name)" }
    if ($VpsIP -eq $lock.forbid_vps_ip) { Die "Refusing forbidden VPS: $VpsIP" }
    if ($lock.remote_root -eq $lock.forbid_remote_root) { Die "Refusing forbidden remote root in lock: $($lock.remote_root)" }
    if ($VpsIP -ne $lock.vps_ip) { Die "VPS mismatch: requested $VpsIP, lock requires $($lock.vps_ip)" }
    if ($lock.remote_root -ne "/var/www/chainreporter") { Die "Remote root mismatch: lock requires /var/www/chainreporter, got $($lock.remote_root)" }
    if ($lock.backend_service -ne "chainreporter-backend") { Die "Backend service mismatch: $($lock.backend_service)" }
    if ($lock.frontend_service -ne "chainreporter-frontend") { Die "Frontend service mismatch: $($lock.frontend_service)" }
}

function Assert-LocalIdentity($root) {
    $backendPackage = Join-Path $root "backend\package.json"
    if (Test-Path $backendPackage) {
        $pkg = Get-Content -Raw $backendPackage | ConvertFrom-Json
        if ($pkg.name -ne "chainreporter-backend") { Die "Local backend package identity mismatch: $($pkg.name)" }
    }

    if (-not (Test-Path (Join-Path $root "backend")) -or -not (Test-Path (Join-Path $root "frontend"))) {
        Die "Local project shape does not look like ChainReporter: expected backend/ and frontend/ folders."
    }
}

$LockPath = Join-Path $ProjectRoot "DEPLOYMENT_TARGET.lock"
$DeploymentLock = Read-DeploymentLock $LockPath
Assert-DeploymentTarget $DeploymentLock
Assert-LocalIdentity $ProjectRoot

$RemoteRoot = $DeploymentLock.remote_root
$BackendService = $DeploymentLock.backend_service
$FrontendService = $DeploymentLock.frontend_service

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ChainReporter VPS Deploy (per-file)"      -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VPS:        $VpsUser@$VpsIP"
Write-Host "  RemoteRoot: $RemoteRoot"
Write-Host "  Project:    $ProjectRoot"
Write-Host "  Source:     $(if ($Files) { 'explicit -Files list' } else { "git diff vs $Since" })"
Write-Host "  DryRun:     $DryRun"
Write-Host "  SkipRestart: $SkipRestart"
Write-Host "  SSH key:    $SshKeyPath"

$PreparedSshKeyPath = Prepare-SshKeyForCurrentUser $SshKeyPath
Ok "Prepared sandbox-readable SSH key"

# SSH/SCP shared options.
# -o LogLevel=ERROR suppresses ssh's "Permanently added" host-key notice on
# stderr (cosmetic noise). $LASTEXITCODE is still checked on every call so real
# failures still abort via Die().
$SshOpts = @("-i", $PreparedSshKeyPath, "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR")
$Target  = "${VpsUser}@${VpsIP}"

function Assert-RemoteIdentity {
    Step "Verifying remote identity..."

    $remoteCheck = @"
set -eu
ROOT='$RemoteRoot'
FORBID_ROOT='$($DeploymentLock.forbid_remote_root)'
if [ "`$ROOT" = "`$FORBID_ROOT" ]; then
  echo REMOTE_ID_FORBIDDEN_ROOT
  exit 20
fi
if [ ! -d "`$ROOT" ]; then
  echo REMOTE_ID_EMPTY
  exit 0
fi
if [ -z "`$(find "`$ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  echo REMOTE_ID_EMPTY
  exit 0
fi
if [ -f "`$ROOT/DEPLOYMENT_TARGET.lock" ]; then
  if grep -qx 'project_id=chainreporter' "`$ROOT/DEPLOYMENT_TARGET.lock" && grep -qx 'project_name=ChainReporter' "`$ROOT/DEPLOYMENT_TARGET.lock"; then
    echo REMOTE_ID_CHAINREPORTER_LOCK
    exit 0
  fi
  echo REMOTE_ID_UNKNOWN_LOCK
  exit 22
fi
if [ -f "`$ROOT/backend/package.json" ]; then
  if grep -q '"name"[[:space:]]*:[[:space:]]*"chainreporter-backend"' "`$ROOT/backend/package.json"; then
    echo REMOTE_ID_CHAINREPORTER_PACKAGE
    exit 0
  fi
fi
if [ -f "`$ROOT/backend/config.py" ]; then
  if grep -q "MEDIA_LIST = \\['RZ Prime', 'Coin Hall', 'ChainReporter', 'Meta Coin Guard'\\]" "`$ROOT/backend/config.py"; then
    echo REMOTE_ID_CHAINREPORTER_CONFIG
    exit 0
  fi
fi
echo REMOTE_ID_NO_IDENTITY_FILE
exit 23
"@

    $remoteOut = ssh @SshOpts $Target $remoteCheck 2>&1
    $code = $LASTEXITCODE
    Write-Host ($remoteOut -join "`n")

    if ($code -eq 0) {
        if ($remoteOut -contains "REMOTE_ID_EMPTY") {
            if ($RemoteRoot -ne "/var/www/chainreporter") { Die "Remote folder is empty but path is not /var/www/chainreporter." }
            Warn "Remote folder is empty or missing; first deploy allowed only because path is exactly /var/www/chainreporter."
        } else {
            Ok "Remote identity verified as ChainReporter"
        }
        return
    }

    if (($remoteOut -join "`n") -match "REMOTE_ID_FORBIDDEN_ROOT") { Die "Remote root is forbidden; aborting before upload." }
    Die "Remote identity could not be verified as ChainReporter; aborting before upload."
}

# ── 1. Determine which files to deploy ────────────────────────────────────────
if ($Files) {
    $changed = $Files -split ',' | ForEach-Object { ($_.Trim() -replace '\\', '/') } | Where-Object { $_ }
} else {
    Step "Detecting changed files vs $Since"
    # EAP is "Continue" so git's CRLF warning on stderr won't crash us; we filter
    # to plain non-empty strings to drop the warning text and any ErrorRecords.
    $tracked   = @(git diff --name-only --diff-filter=ACMR $Since 2>&1)
    $untracked = @(git ls-files --others --exclude-standard 2>&1)
    $changed   = @($tracked + $untracked | Where-Object { $_ -is [string] -and $_.Trim() }) | Sort-Object -Unique
}

# Only backend/* and frontend/src/* are deployable. Exclude data/.env/caches.
function IsDeployable($rel) {
    if ($rel -notmatch '^(backend|frontend/src)/') { return $false }
    if ($rel -like 'backend/data/*' -or $rel -eq 'backend/data') { return $false }
    if ($rel -eq 'backend/.env' -or $rel -like 'backend/__pycache__/*') { return $false }
    if ($rel -like '*/*.pyc' -or $rel -like 'backend/*.log' -or $rel -like 'backend/*.pid') { return $false }
    return $true
}

$toDeploy = @($changed | Where-Object { IsDeployable $_ } | Sort-Object -Unique)

if ($toDeploy.Count -eq 0) {
    Warn "No deployable changed files found."
    Write-Host "    (backend/data/ and .env are always skipped.)"
    Write-Host "    Use -Files path1,path2 to deploy an explicit list."
    exit 0
}

Step "Files to deploy ($($toDeploy.Count)):"
foreach ($f in $toDeploy) {
    $localFull = Join-Path $ProjectRoot ($f -replace '/', '\')
    $tag = if (Test-Path $localFull) { '[ok ]' } else { '[MISS]' }
    Write-Host "    $tag $f"
}
$missing = $toDeploy | Where-Object { -not (Test-Path (Join-Path $ProjectRoot ($_ -replace '/', '\'))) }
if ($missing) { Die "Some files missing locally -- create/commit them first: $($missing -join ', ')" }

if ($DryRun) { Warn "DryRun set -- stopping before upload."; exit 0 }


# ── 2. Test SSH ───────────────────────────────────────────────────────────────
Step "Testing SSH connection..."
$test = ssh @SshOpts $Target "echo OK" 2>$null
if ($LASTEXITCODE -ne 0 -or $test -ne "OK") { Die "SSH connection failed to $Target" }
Ok "SSH OK"

Assert-RemoteIdentity

Step "Installing remote deployment lock..."
scp @SshOpts "$LockPath" "${Target}:$RemoteRoot/DEPLOYMENT_TARGET.lock" | Out-Null
if ($LASTEXITCODE -ne 0) { Die "Failed to install remote deployment lock." }
Ok "Remote deployment lock installed"

# ── 3. Upload each file (mkdir -p parent on VPS first for new folders) ─────────
Step "Uploading changed files..."
foreach ($rel in $toDeploy) {
    $localFull = Join-Path $ProjectRoot ($rel -replace '/', '\')
    $remote    = "$RemoteRoot/$rel"
    $remoteDir = $remote -replace '/[^/]+$', ''
    ssh @SshOpts $Target "mkdir -p $remoteDir" | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "mkdir -p failed for $remoteDir" }
    scp @SshOpts "$localFull" "${Target}:$remote" | Out-Null
    if ($LASTEXITCODE -ne 0) { Die "scp failed: $rel" }
    Ok $rel
}

if ($SkipRestart) { Warn "-SkipRestart set - files uploaded, no build/restart."; exit 0 }

# ── 4. Backend: syntax check + restart (only if backend files changed) ────────
$hasBackend = @($toDeploy | Where-Object { $_ -like 'backend/*' })
if ($hasBackend.Count -gt 0) {
    Step "Backend: syntax check on VPS..."
    # py_compile compiles to bytecode without running imports -- clean syntax check.
    # Plain string, no inner quotes, so PowerShell 5.1 won't choke.
    $checkOut = ssh @SshOpts $Target "cd $RemoteRoot/backend; python3 -m py_compile *.py; echo EXIT_$LASTEXITCODE" 2>&1
    if (($checkOut -join ' ') -notmatch 'EXIT_0') {
        Write-Host $checkOut
        Die "Backend syntax check FAILED -- service NOT restarted. Fix and redeploy."
    }
    Ok "Backend syntax OK"

    Step "Restarting backend..."
    $beOut = ssh @SshOpts $Target "chown -R www-data:www-data $RemoteRoot/backend; systemctl restart $BackendService; sleep 3; systemctl is-active $BackendService" 2>&1
    Write-Host ($beOut -join "`n")
    if (-not ($beOut -contains 'active')) { Die "Backend did not come up active." }
    Ok "Backend active"
}

# ── 5. Frontend: build on VPS + restart (only if frontend files changed) ──────
$hasFrontend = @($toDeploy | Where-Object { $_ -like 'frontend/src/*' })
if ($hasFrontend.Count -gt 0) {
    Step "Building frontend on VPS..."
    $buildOut = ssh @SshOpts $Target "cd $RemoteRoot/frontend; npm run build 2>&1 | tail -8; chown -R www-data:www-data dist; echo BUILD_DONE" 2>&1
    Write-Host ($buildOut -join "`n")
    if (-not ($buildOut -contains 'BUILD_DONE')) { Die "Frontend build failed on VPS." }
    Ok "Frontend built"

    Step "Restarting frontend..."
    $feOut = ssh @SshOpts $Target "systemctl restart $FrontendService; systemctl is-active $FrontendService" 2>&1
    Write-Host ($feOut -join "`n")
    if (-not ($feOut -contains 'active')) { Die "Frontend did not come up active." }
    Ok "Frontend active"
}

if ($hasBackend.Count -eq 0 -and $hasFrontend.Count -eq 0) {
    Warn "No backend/frontend files -- nothing to build or restart."
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deploy complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Website:  http://$VpsIP/login"
Write-Host "  Health:   http://$VpsIP/api/health"
Write-Host "  Logs:     ssh -i $PreparedSshKeyPath $Target journalctl -u $BackendService -n 30 --no-pager"
Write-Host ""
