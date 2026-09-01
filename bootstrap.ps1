# RecoverAI - one-line bootstrap for Windows PowerShell.
# Clones the repo (or updates it if already present) and starts the whole
# app with Docker Compose. Nothing else needs to be installed first except
# Docker Desktop and git.
#
# Usage:
#   irm https://raw.githubusercontent.com/harinish45/AI-Revenue-Recovery/main/bootstrap.ps1 | iex

$ErrorActionPreference = "Stop"
$repoUrl = "https://github.com/harinish45/AI-Revenue-Recovery.git"
$dirName = "AI-Revenue-Recovery"

Write-Host ""
Write-Host "  RecoverAI - cloning and starting..." -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: git is required. Install it from https://git-scm.com/downloads then re-run this command." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $dirName)) {
    Write-Host "[1/2] Cloning repository into .\$dirName ..."
    git clone --depth 1 $repoUrl $dirName
} else {
    Write-Host "[1/2] .\$dirName already exists - pulling the latest changes..."
    Push-Location $dirName
    try { git pull --ff-only } catch { Write-Host "  (couldn't fast-forward -- using what's already there)" }
    Pop-Location
}

Set-Location $dirName

$dockerOk = $false
try {
    docker compose version | Out-Null
    $dockerOk = $true
} catch {
    $dockerOk = $false
}

if (-not $dockerOk) {
    Write-Host ""
    Write-Host "ERROR: Docker was not found (or Docker Desktop isn't running)." -ForegroundColor Red
    Write-Host "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    Write-Host "then re-run this command from inside .\$dirName :"
    Write-Host "  docker compose up --build"
    exit 1
}

Write-Host "[2/2] Starting with Docker Compose (first run downloads and builds images, a couple of minutes)..."
docker compose up --build -d

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Green
Write-Host "    RecoverAI is running!" -ForegroundColor Green
Write-Host "      App  : http://localhost:8000"
Write-Host "    Stop it any time with: docker compose down"
Write-Host "  ================================================" -ForegroundColor Green
Write-Host ""

Start-Process "http://localhost:8000"
