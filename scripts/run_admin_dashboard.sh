#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then
  PYTHON="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
else
  echo "Program error: Python not found. Please create .venv or install Python."
  exit 1
fi

if [ "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
else
  export PYTHONPATH="$PROJECT_ROOT/src"
fi

cd "$PROJECT_ROOT"
echo "market_price_guard local admin dashboard"
echo "Open: http://127.0.0.1:8766/admin"
exec "$PYTHON" -m market_price_guard.admin_app --host 127.0.0.1 --port 8766 --project-root "$PROJECT_ROOT"
