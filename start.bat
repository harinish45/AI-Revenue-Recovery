@echo off
setlocal EnableDelayedExpansion
title RecoverAI - one-command launcher
cd /d "%~dp0"

echo.
echo   RecoverAI - one-command setup + launch...
echo.

REM ---------- 1. pick the newest usable Python (3.10-3.13; pydantic needs wheels, avoid 3.13+) ----------
set "PYCMD="
for %%V in (3.12 3.11 3.10 3.13) do (
    if not defined PYCMD (
        py -%%V --version >nul 2>&1 && set "PYCMD=py -%%V"
    )
)
if not defined PYCMD (
    python --version >nul 2>&1 && set "PYCMD=python"
)

REM ---------- Python not found anywhere: install it automatically via winget ----------
if not defined PYCMD (
    echo [1/4] Python not found - installing it automatically via winget...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo   ERROR: winget is not available on this machine.
        echo   Install Python 3.10-3.12 manually: https://www.python.org/downloads/
        echo   ^(winget ships with Windows 10 2004+ and Windows 11 - update App Installer from the Microsoft Store if missing.^)
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.11 -e --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo   ERROR: winget install failed. Install Python manually: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo   Python installed. Re-checking...
    REM winget updates PATH for new terminals, not this one -- refresh from the registry.
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "PATH=%%B;%PATH%"
    for %%V in (3.12 3.11 3.10 3.13) do (
        if not defined PYCMD (
            py -%%V --version >nul 2>&1 && set "PYCMD=py -%%V"
        )
    )
    if not defined PYCMD (
        python --version >nul 2>&1 && set "PYCMD=python"
    )
    if not defined PYCMD (
        echo   Python was installed but isn't on PATH in this window yet.
        echo   Close this window and run start.bat again from a fresh terminal.
        pause
        exit /b 1
    )
)
echo [1/4] Using Python: !PYCMD!

REM ---------- 2. backend venv + dependencies ----------
if exist "backend\venv\Scripts\python.exe" goto :deps

echo [2/4] Creating backend virtualenv ^(first run only^)...
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
echo [3/4] Installing backend dependencies ^(skipped if already present^)...
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

findstr /R /C:"^RAZORPAY_KEY_ID=.+" .env >nul 2>&1
if errorlevel 1 echo   NOTE: Razorpay keys not set in .env - running in simulated (Test Mode) demo.

:launch
echo [4/4] Starting RecoverAI on :8000 ...
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
