# Contributing to Track Maintenance

Thank you for your interest in contributing. This project is a companion service for [Traccar](https://www.traccar.org/) — please read the README and `agents.md` before making changes.

## Development setup

1. Copy `.env.example` to `.env` and configure MySQL + Traccar URLs.
2. Backend:
   ```bash
   cd backend
   python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
   .venv/bin/alembic upgrade head
   .venv/bin/uvicorn app.main:app --reload
   ```
3. Frontend:
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
- Do not add uvicorn workers (breaks APScheduler and in-memory caches).
- Never query or write to Traccar's database — integration is REST API only.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
