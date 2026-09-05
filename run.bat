@echo off
title StudyQuest
cd /d "%~dp0"

if not exist venv (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo Starting StudyQuest at http://127.0.0.1:8000/
echo Press Ctrl+C to stop.
python manage.py runserver
pause
