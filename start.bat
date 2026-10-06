@echo off
REM UGCORA Studio - one-command local launcher (Windows)
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [UGCORA] Studio local launcher
echo [UGCORA] Working dir: %cd%

REM 1. Create venv if missing
if not exist "venv\" (
  echo [UGCORA] Creating virtual environment...
  python -m venv venv
  if errorlevel 1 (
    echo [ERROR] Could not create venv. Install Python 3.11+ from python.org.
    pause
    exit /b 1
  )
)

REM 2. Activate venv
call venv\Scripts\activate.bat

REM 3. Install deps if missing
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
  echo [UGCORA] Installing dependencies...
  python -m pip install --upgrade pip >nul
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
  )
)

REM 4. Create .env from template on first run
if not exist ".env" (
  echo [UGCORA] Creating .env from .env.example
  copy .env.example .env >nul
  echo.
  echo [IMPORTANT] Edit .env to set:
  echo   - ADMIN_USERNAME / ADMIN_PASSWORD   (your login)
  echo   - GEMINI_API_KEY                    (for product analysis and scripts)
  echo   - NVIDIA_API_KEY / NVIDIA_MODEL     (for video generation)
  echo.
  echo [UGCORA] Then re-run: start.bat
  pause
  exit /b 0
)

REM 5. Run
echo [UGCORA] Starting at http://127.0.0.1:8000
python run.py
pause
