#!/usr/bin/env bash
# RecoverAI — true one-command launcher (macOS / Linux).
# If Python itself isn't installed, this installs it for you (Homebrew on
# macOS, apt/dnf/pacman/zypper on Linux) before setting up the venv and
# starting the app. Re-run any time — every step is skip-if-already-done.
set -e
cd "$(dirname "$0")"

echo ""
echo "  RecoverAI — one-command setup + launch..."
echo ""

find_python() {
    for cand in python3.12 python3.11 python3.10 python3.13 python3; do
        if command -v "$cand" >/dev/null 2>&1; then echo "$cand"; return 0; fi
    done
    return 1
}

# ---------- 1. Python: find it, or install it ----------
PYCMD="$(find_python || true)"
if [ -z "$PYCMD" ]; then
    echo "[1/4] Python not found — installing it automatically..."
    OS_NAME="$(uname -s)"
    if [ "$OS_NAME" = "Darwin" ]; then
        if ! command -v brew >/dev/null 2>&1; then
            echo "        Homebrew not found — installing Homebrew first (this needs your sudo password)..."
            NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            # Apple Silicon Homebrew installs to /opt/homebrew, not on PATH yet in this shell.
            [ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
            [ -x /usr/local/bin/brew ] && eval "$(/usr/local/bin/brew shellenv)"
        fi
        brew install python@3.11
    elif [ "$OS_NAME" = "Linux" ]; then
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update -y && sudo apt-get install -y python3 python3-venv python3-pip
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y python3 python3-pip
        elif command -v pacman >/dev/null 2>&1; then
            sudo pacman -Sy --noconfirm python python-pip
        elif command -v zypper >/dev/null 2>&1; then
            sudo zypper install -y python3 python3-pip
        else
            echo "ERROR: no supported package manager found (apt/dnf/pacman/zypper)."
            echo "Install Python 3.10-3.12 manually: https://www.python.org/downloads/"
            exit 1
        fi
    else
        echo "ERROR: unrecognized OS '$OS_NAME'."
        echo "Install Python 3.10-3.12 manually: https://www.python.org/downloads/"
        exit 1
    fi
    PYCMD="$(find_python || true)"
    if [ -z "$PYCMD" ]; then
        echo "ERROR: Python install completed but no python3 was found on PATH. Open a new terminal and re-run ./start.sh."
        exit 1
    fi
fi
echo "[1/4] Using Python: $($PYCMD --version)"

# ---------- 2. backend venv ----------
if [ ! -f backend/venv/bin/python ] && [ ! -f backend/venv/Scripts/python.exe ]; then
    echo "[2/4] Creating backend virtualenv (first run only)..."
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

echo "[3/4] Installing backend dependencies (skipped if already present)..."
"$VPY" -m pip install --quiet --disable-pip-version-check -r backend/requirements.txt
"$VPY" -m pip install --quiet --disable-pip-version-check "setuptools<81" >/dev/null 2>&1 || true

[ -f .env ] || cp .env.example .env
[ -f backend/.env ] || cp .env backend/.env

if [ -z "$(grep -E '^RAZORPAY_KEY_ID=.+' .env 2>/dev/null)" ]; then
    echo "  NOTE: Razorpay keys not set in .env — running in simulated (Test Mode) demo."
fi

# ---------- 4. launch ----------
echo "[4/4] Starting RecoverAI on :8000 ..."
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
