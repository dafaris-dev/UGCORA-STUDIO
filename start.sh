#!/usr/bin/env bash
# UGCORA Studio - one-command local launcher (macOS / Linux)
set -e

cd "$(dirname "$0")"

PY=${PYTHON:-python3}

echo "▸ UGCORA Studio - local launcher"
echo "▸ Working dir: $(pwd)"

# 1. Create venv if missing
if [ ! -d "venv" ]; then
  echo "▸ Creating virtual environment..."
  $PY -m venv venv
fi

# 2. Activate venv
# shellcheck disable=SC1091
source venv/bin/activate

# 3. Install deps (quiet, only if needed)
if ! python -c "import fastapi" >/dev/null 2>&1; then
  echo "▸ Installing dependencies..."
  pip install --upgrade pip >/dev/null
  pip install -r requirements.txt
fi

# 4. Create .env from template on first run
if [ ! -f ".env" ]; then
  echo "▸ Creating .env from .env.example"
  cp .env.example .env
  # Give it a random session secret
  if command -v openssl >/dev/null 2>&1; then
    SECRET=$(openssl rand -hex 32)
    sed -i.bak "s|^SESSION_SECRET=.*|SESSION_SECRET=$SECRET|" .env && rm -f .env.bak
  fi
  echo ""
  echo "▸▸ IMPORTANT: edit .env to set:"
  echo "   - ADMIN_USERNAME / ADMIN_PASSWORD   (your login)"
  echo "   - GEMINI_API_KEY                    (for product analysis & scripts)"
  echo "   - NVIDIA_API_KEY / NVIDIA_MODEL     (for video generation)"
  echo ""
  echo "▸▸ Then re-run: ./start.sh"
  exit 0
fi

# 5. Run
echo "▸ Starting UGCORA Studio at http://127.0.0.1:${APP_PORT:-8000}"
exec python run.py
