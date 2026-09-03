#!/usr/bin/env bash
# StudyQuest - first-time setup (macOS/Linux)
set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "  StudyQuest - first-time setup"
echo "=========================================="

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 was not found on PATH."
    echo "Install Python 3.11+ and re-run this script."
    exit 1
fi

if [ ! -d venv ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/4] Virtual environment already exists, skipping."
fi

echo "[2/4] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

echo "[3/4] Setting up the database..."
python manage.py migrate

echo "[4/4] Optional: create an admin account for /admin/"
read -p "Create a superuser now? (y/N): " makesuper
if [[ "$makesuper" =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

echo
echo "=========================================="
echo "  Setup complete!"
echo "  Run ./run.sh any time to start the app."
echo "=========================================="
