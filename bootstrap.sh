#!/usr/bin/env bash
# RecoverAI — one-line bootstrap for macOS / Linux.
# Clones the repo (or updates it if already present) and starts the whole
# app with Docker Compose. Nothing else needs to be installed first except
# Docker and git.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/harinish45/AI-Revenue-Recovery/main/bootstrap.sh | bash
set -e

REPO_URL="https://github.com/harinish45/AI-Revenue-Recovery.git"
DIR_NAME="AI-Revenue-Recovery"

echo ""
echo "  RecoverAI — cloning and starting..."
echo ""

if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required. Install it from https://git-scm.com/downloads then re-run this command."
    exit 1
fi

if [ ! -d "$DIR_NAME" ]; then
    echo "[1/2] Cloning repository into ./$DIR_NAME ..."
    git clone --depth 1 "$REPO_URL" "$DIR_NAME"
else
    echo "[1/2] ./$DIR_NAME already exists — pulling the latest changes..."
    (cd "$DIR_NAME" && git pull --ff-only) || echo "  (couldn't fast-forward — using what's already there)"
fi

cd "$DIR_NAME"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo ""
    echo "ERROR: Docker was not found (or isn't running)."
    echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    echo "then re-run this command from inside ./$DIR_NAME:"
    echo "  docker compose up --build"
    exit 1
fi

echo "[2/2] Starting with Docker Compose (first run downloads and builds images, a couple of minutes)..."
docker compose up --build -d

echo ""
echo "  ================================================"
echo "    RecoverAI is running!"
echo "      App  : http://localhost:8000"
echo "    Stop it any time with: docker compose down"
echo "  ================================================"
echo ""

( command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:8000 ) \
  || ( command -v open >/dev/null 2>&1 && open http://localhost:8000 ) || true
