@echo off
setlocal enabledelayedexpansion
title StudyQuest Setup
cd /d "%~dp0"

echo ==========================================
echo   StudyQuest - first-time setup
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.11+ from https://www.python.org/downloads/ and re-run this script.
    pause
    exit /b 1
)

if not exist venv (
    echo [1/4] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/4] Virtual environment already exists, skipping.
)

echo [2/4] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [3/4] Setting up the database...
python manage.py migrate
if errorlevel 1 (
    echo [ERROR] Migration failed.
    pause
    exit /b 1
)

echo [4/4] Optional: create an admin account for /admin/
set /p makesuper="Create a superuser now? (y/N): "
if /i "%makesuper%"=="y" (
    python manage.py createsuperuser
)

echo.
echo ==========================================
echo   Setup complete!
echo   Run "run.bat" any time to start the app.
echo ==========================================
pause
