# Contributing to Track Maintenance

Thank you for your interest in contributing. This project is a companion service for [Traccar](https://www.traccar.org/) — please read the README and `agents.md` before making changes.

## Development setup

1. Copy dev environment file (uses Docker MySQL on port 3307):
   ```bash
   cp .env.dev.example .env
   ```
2. Start everything:
   ```bash
   ./scripts/dev.sh
   ```
   Or start MySQL + migrations only: `./scripts/dev-db.sh migrate`
3. Traccar must be reachable at `TRACCAR_URL` for login (SSH-forward port 8082 if remote).

Backend-only after DB is up:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload
```

Frontend (separate terminal if not using `./scripts/dev.sh`):

```bash
cd frontend
npm install
npm run dev
```

## Tests

Run the backend test suite before opening a PR:

```bash
cd backend && .venv/bin/python -m pytest
```

Tests use mocked Traccar and an in-memory SQLite database — no live MySQL or Traccar required.

## Pull requests

- Keep diffs focused; avoid unrelated refactors.
- Match existing naming, error handling, and patterns in neighboring files.
- User-visible strings belong in `frontend/src/i18n/` (not hardcoded in JSX).
- Backend schema changes need an Alembic migration in `backend/app/alembic/versions/`.
- Do not add uvicorn workers (breaks in-memory auth caches).
- Never query or write to Traccar's database — integration is REST API only.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
