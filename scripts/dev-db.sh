#!/usr/bin/env bash
# Start/stop the local MySQL container and run Alembic migrations.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.dev.yml)

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required for local MySQL. Install Docker Desktop or Podman, then retry." >&2
    exit 1
  fi
}

ensure_env() {
  if [[ ! -f .env ]]; then
    cp .env.dev.example .env
    echo "Created .env from .env.dev.example"
  fi
}

ensure_backend_venv() {
  if [[ ! -d backend/.venv ]]; then
    echo "Creating backend virtualenv..."
    python3 -m venv backend/.venv
    backend/.venv/bin/pip install -q -e "backend/.[dev]"
  fi
}

cmd_up() {
  require_docker
  "${COMPOSE[@]}" up -d --wait mysql
  echo "MySQL ready at 127.0.0.1:3307 (database: track_maintenance)"
}

cmd_down() {
  require_docker
  "${COMPOSE[@]}" down
}

cmd_migrate() {
  cmd_up
  ensure_env
  ensure_backend_venv
  echo "Running Alembic migrations..."
  (cd backend && .venv/bin/alembic upgrade head)
  echo "Migrations applied."
}

cmd_status() {
  require_docker
  "${COMPOSE[@]}" ps
}

usage() {
  cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  up        Start MySQL and wait until healthy (default)
  down      Stop MySQL container
  migrate   Start MySQL, ensure .env + venv, run Alembic migrations
  status    Show container status

Examples:
  ./scripts/dev-db.sh up
  ./scripts/dev-db.sh migrate
EOF
}

main() {
  local cmd="${1:-up}"
  case "$cmd" in
    up) cmd_up ;;
    down) cmd_down ;;
    migrate) cmd_migrate ;;
    status) cmd_status ;;
    -h|--help|help) usage ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
