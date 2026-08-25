@echo off
setlocal EnableDelayedExpansion
title RecoverAI - one-command launcher
cd /d "%~dp0"

echo.
echo   RecoverAI - starting backend (serves the full app)...
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
echo [1/3] Using Python: !PYCMD!

REM ---------- 2. backend venv + dependencies ----------
if exist "backend\venv\Scripts\python.exe" goto :deps

echo [2/3] Creating backend virtualenv ^(first run only^)...
where uv >nul 2>nul
if not errorlevel 1 (
    REM uv can auto-download a compatible Python (pydantic needs prebuilt wheels)
    pushd backend
    uv venv venv --python 3.11 || goto :fail
    uv pip install --python venv\Scripts\python.exe -r requirements.txt || goto :fail
    uv pip install --python venv\Scripts\python.exe "setuptools<81" >nul 2>&1
    popd
    goto :launch
)
pushd backend
%PYCMD% -m venv venv || goto :fail
popd

:deps
echo [2/3] Installing backend dependencies ^(skipped if already present^)...
where uv >nul 2>nul
if not errorlevel 1 (
    uv pip install --python backend\venv\Scripts\python.exe -r backend\requirements.txt || goto :fail
    uv pip install --python backend\venv\Scripts\python.exe "setuptools<81" >nul 2>&1
) else (
    backend\venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r backend\requirements.txt || goto :fail
    backend\venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check "setuptools<81" >nul 2>&1
)

if not exist ".env" copy .env.example .env >nul
if not exist "backend\.env" copy .env backend\.env >nul

:launch
echo [3/3] Starting RecoverAI on :8000 ...
start "RecoverAI" cmd /k "cd backend && venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
timeout /t 4 /nobreak >nul

start "" http://localhost:8000/

echo.
echo   ================================================
echo     RecoverAI is running!
echo       App  : http://localhost:8000
echo       Docs : http://localhost:8000/docs
echo     Close the server window to stop.
echo   ================================================
echo.
goto :eof

:fail
echo.
echo   ERROR: setup failed. Check the messages above.
pause
exit /b 1
