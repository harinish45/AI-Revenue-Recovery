#!/usr/bin/env bash
# RecoverAI — one-command launcher (macOS / Linux)
set -e
cd "$(dirname "$0")"

echo ""
echo "  RecoverAI — starting backend (serves the full app)..."
echo ""

# ---------- 1. pick Python (3.10–3.12 recommended; pydantic needs prebuilt wheels) ----------
PYCMD=""
for cand in python3.12 python3.11 python3.10 python3.13 python3; do
    if command -v "$cand" >/dev/null 2>&1; then PYCMD="$cand"; break; fi
done
[ -z "$PYCMD" ] && { echo "ERROR: no python found"; exit 1; }
echo "[1/3] Using Python: $($PYCMD --version)"

# ---------- 2. backend venv ----------
if [ ! -f backend/venv/bin/python ] && [ ! -f backend/venv/Scripts/python.exe ]; then
    echo "[2/3] Creating backend virtualenv (first run only)..."
    if command -v uv >/dev/null 2>&1; then
        # uv auto-downloads a compatible Python (pydantic needs prebuilt wheels)
        (cd backend && uv venv venv --python 3.11 \
            && uv pip install --python venv/bin/python -r requirements.txt \
            && uv pip install --python venv/bin/python "setuptools<81" || true)
    else
        (cd backend && "$PYCMD" -m venv venv)
    fi
fi

VPY="backend/venv/bin/python"
[ -f "$VPY" ] || VPY="backend/venv/Scripts/python.exe"

echo "[2/3] Installing backend dependencies (skipped if already present)..."
"$VPY" -m pip install --quiet --disable-pip-version-check -r backend/requirements.txt
"$VPY" -m pip install --quiet --disable-pip-version-check "setuptools<81" >/dev/null 2>&1 || true

[ -f .env ] || cp .env.example .env
[ -f backend/.env ] || cp .env backend/.env

# ---------- 3. launch ----------
echo "[3/3] Starting RecoverAI on :8000 ..."
(cd backend && ./venv/bin/python -m uvicorn app.main:app --port 8000) &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT INT TERM
sleep 4

echo ""
echo "  ================================================"
echo "    RecoverAI is running!"
echo "      App  : http://localhost:8000"
echo "      Docs : http://localhost:8000/docs"
echo "    Press Ctrl+C to stop the server."
echo "  ================================================"
echo ""

# open browser (best effort)
( command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:8000 ) \
  || ( command -v open >/dev/null 2>&1 && open http://localhost:8000 ) || true

wait
