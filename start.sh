#!/usr/bin/env bash
# RecoverAI — one-command launcher (macOS / Linux)
set -e
cd "$(dirname "$0")"

echo ""
echo "  RecoverAI — starting backend + frontend..."
echo ""

# ---------- 1. pick Python (3.10–3.12 recommended; pydantic needs prebuilt wheels) ----------
PYCMD=""
for cand in python3.12 python3.11 python3.10 python3.13 python3; do
    if command -v "$cand" >/dev/null 2>&1; then PYCMD="$cand"; break; fi
done
[ -z "$PYCMD" ] && { echo "ERROR: no python found"; exit 1; }
echo "[1/5] Using Python: $($PYCMD --version)"

# ---------- 2. backend venv ----------
if [ ! -f backend/venv/bin/python ] && [ ! -f backend/venv/Scripts/python.exe ]; then
    echo "[2/5] Creating backend virtualenv (first run only)..."
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

echo "[3/5] Installing backend dependencies (skipped if already present)..."
"$VPY" -m pip install --quiet --disable-pip-version-check -r backend/requirements.txt
"$VPY" -m pip install --quiet --disable-pip-version-check "setuptools<81" >/dev/null 2>&1 || true

[ -f backend/.env ] || cp backend/.env.example backend/.env

# ---------- 3. frontend deps ----------
if [ ! -d frontend/node_modules ]; then
    echo "      Installing frontend dependencies (first run only, ~30s)..."
    (cd frontend && npm install --no-fund --no-audit)
fi
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env
echo "[4/5] Dependencies ready."

# ---------- 4. launch ----------
echo "[5/5] Starting API on :8000 and web app on :5173 ..."
(cd backend && ./venv/bin/python -m uvicorn app.main:app --port 8000) &
API_PID=$!
sleep 4
(cd frontend && npm run dev) &
WEB_PID=$!
trap 'kill $API_PID $WEB_PID 2>/dev/null' EXIT INT TERM
sleep 6

echo ""
echo "  ================================================"
echo "    RecoverAI is running!"
echo "      UI  : http://localhost:5173"
echo "      API : http://localhost:8000/docs"
echo "    Press Ctrl+C to stop both servers."
echo "  ================================================"
echo ""

# open browser (best effort)
( command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:5173 ) \
  || ( command -v open >/dev/null 2>&1 && open http://localhost:5173 ) || true

wait
