#!/usr/bin/env bash
# StudyQuest - start the dev server (macOS/Linux)
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "Virtual environment not found. Run ./setup.sh first."
    exit 1
fi

source venv/bin/activate
echo "Starting StudyQuest at http://127.0.0.1:8000/"
echo "Press Ctrl+C to stop."
python manage.py runserver
