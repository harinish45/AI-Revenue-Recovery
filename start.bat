@echo off
setlocal EnableDelayedExpansion
title RecoverAI - one-command launcher
cd /d "%~dp0"

echo.
echo   RecoverAI - starting backend + frontend...
echo.

REM ---------- 1. pick the newest usable Python (3.10-3.13; pydantic needs wheels, avoid 3.13+) ----------
set "PYCMD=python"
for %%V in (3.12 3.11 3.10 3.13) do (
    py -%%V --version >nul 2>&1 && (
        set "PYCMD=py -%%V"
        goto :havepy
    )
)
:havepy
echo [1/5] Using Python: !PYCMD!

REM ---------- 2. backend venv + dependencies ----------
if exist "backend\venv\Scripts\python.exe" goto :deps

echo [2/5] Creating backend virtualenv ^(first run only^)...
where uv >nul 2>nul
if not errorlevel 1 (
    REM uv can auto-download a compatible Python (pydantic needs prebuilt wheels)
    pushd backend
    uv venv venv --python 3.11 || goto :fail
    uv pip install --python venv\Scripts\python.exe -r requirements.txt || goto :fail
    uv pip install --python venv\Scripts\python.exe "setuptools<81" >nul 2>&1
    popd
    goto :frontend
)
pushd backend
%PYCMD% -m venv venv || goto :fail
popd

:deps
echo [3/5] Installing backend dependencies ^(skipped if already present^)...
where uv >nul 2>nul
if not errorlevel 1 (
    uv pip install --python backend\venv\Scripts\python.exe -r backend\requirements.txt || goto :fail
    uv pip install --python backend\venv\Scripts\python.exe "setuptools<81" >nul 2>&1
) else (
    backend\venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r backend\requirements.txt || goto :fail
    backend\venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check "setuptools<81" >nul 2>&1
)

if not exist "backend\.env" copy backend\.env.example backend\.env >nul

:frontend
REM ---------- 3. frontend dependencies ----------
if not exist "frontend\node_modules" (
    echo       Installing frontend dependencies ^(first run only, ~30s^)...
    pushd frontend
    call npm install --no-fund --no-audit || goto :fail
    popd
)
if not exist "frontend\.env" copy frontend\.env.example frontend\.env >nul
echo [4/5] Dependencies ready.

REM ---------- 4. launch servers in their own windows ----------
echo [5/5] Starting API on :8000 and web app on :5173 ...
start "RecoverAI API" cmd /k "cd backend && venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
timeout /t 4 /nobreak >nul
start "RecoverAI Web" cmd /k "cd frontend && npm run dev"
timeout /t 6 /nobreak >nul

start "" http://localhost:8000/docs
start "" http://localhost:5173/

echo.
echo   ================================================
echo     RecoverAI is running!
echo       UI  : http://localhost:5173
echo       API : http://localhost:8000/docs
echo     Close the two server windows to stop.
echo   ================================================
echo.
goto :eof

:fail
echo.
echo   ERROR: setup failed. Check the messages above.
pause
exit /b 1
