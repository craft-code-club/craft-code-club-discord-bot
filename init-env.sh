#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== init-env: setting up Python environment ==="
echo ""

# --- .env provisioning ---
if [ -f ".env" ]; then
    echo "[.env] .env already exists — skipping."
elif [ -f ".git" ]; then
    # Worktree: .git is a file containing "gitdir: <path>"
    gitdir_line=$(cat .git)
    if [[ "$gitdir_line" == gitdir:* ]]; then
        gitdir_value="${gitdir_line#gitdir: }"
        root="${gitdir_value%%/.git/*}"
        if [ -f "$root/.env" ]; then
            echo "[.env] Copying .env from main worktree root: $root"
            cp "$root/.env" .env
        else
            if [ -f ".env.example" ]; then
                echo "[.env] No .env in root — copying .env.example"
                cp .env.example .env
            else
                echo "[.env] Warning: no .env.example found. Skipping."
            fi
    else
        echo "[.env] Unexpected .git file format — copying .env.example"
        cp .env.example .env
    fi
else
    # Normal clone: .git is a directory
    if [ -f ".env.example" ]; then
        echo "[.env] Copying .env.example → .env"
        cp .env.example .env
    else
        echo "[.env] Warning: no .env.example found. Skipping."
    fi
fi
echo ""

# --- Python venv ---
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "Error: python3 or python not found. Please install Python 3."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[venv] Creating .venv with $PYTHON..."
    "$PYTHON" -m venv .venv
else
    echo "[venv] .venv already exists — skipping creation."
fi
echo ""

# --- Activate ---
echo "[venv] Activating .venv..."
# shellcheck disable=SC1091
source .venv/bin/activate
echo ""

# --- Upgrade pip ---
echo "[pip] Upgrading pip..."
python -m pip install --upgrade pip
echo ""

# --- Install requirements ---
echo "[pip] Installing requirements..."
pip install -r requirements.txt
echo ""

echo "=== Done! ==="
echo ""
echo "To activate the virtual environment in a new shell:"
echo "  source .venv/bin/activate"
