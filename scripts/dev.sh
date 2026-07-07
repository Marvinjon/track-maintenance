#!/usr/bin/env bash
# One-command local dev: MySQL + migrations, then backend and frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

"$ROOT/scripts/dev-db.sh" migrate

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

ensure_backend_venv() {
  if [[ ! -d backend/.venv ]]; then
    python3 -m venv backend/.venv
    backend/.venv/bin/pip install -q -e "backend/.[dev]"
  fi
}
ensure_backend_venv

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://127.0.0.1:8000 ..."
(cd backend && .venv/bin/uvicorn app.main:app --reload) &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:5173 ..."
echo "Traccar must still be reachable at TRACCAR_URL in .env for login."
(cd frontend && npm run dev)
