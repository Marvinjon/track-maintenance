# Claude guide — Track Maintenance

Read **[agents.md](agents.md)** first for the full project map (layout, APIs, models, constraints, dev commands). This file adds Claude-specific context for working in this repo.

## Quick context

**Track Maintenance** is a Traccar companion app for fleet maintenance tracking and spare-parts inventory. It runs beside a native Traccar + MySQL deployment on Ubuntu. The backend is FastAPI in Docker (host networking); the frontend is a static Vite/React build served by Nginx.

The single most important rule: **never touch Traccar's database**. All device data and auth go through Traccar's REST API. Tenant isolation is enforced by forwarding each user's credentials to Traccar.

## Before you change anything

1. Skim [agents.md](agents.md) — especially "Hard constraints" and "Common agent pitfalls".
2. Check [instructions.md](instructions.md) if the change relates to spec'd behavior (reminders, stock ledger, webhook flow).
3. Read the files you will edit and their nearest neighbors; match naming, patterns, and error handling.
4. Run tests after backend changes: `cd backend && .venv/bin/python -m pytest`.

## How auth actually works (differs from naive Traccar cookie sharing)

The maintenance UI runs on its **own domain** (e.g. `fleet.example.com`), not Traccar's. Users log in with Traccar email/password via `POST /api/v1/auth/login`. The backend validates against Traccar and sets a `maint_session` HttpOnly cookie containing the Traccar session id. The frontend sends this cookie on every API call (`credentials: "include"` in `frontend/src/api/client.ts`).

Bearer tokens (`Authorization: Bearer <traccar-api-token>`) also work for API clients. See `backend/app/api/deps.py`.

## Where things live (cheat sheet)

```
Backend logic:     backend/app/
  Routes:          backend/app/api/*.py
  Business logic:  backend/app/services/*.py
  DB models:       backend/app/models/*.py
  API shapes:      backend/app/schemas/*.py
  Migrations:      backend/app/alembic/versions/
  Tests:           backend/tests/

Frontend:          frontend/src/
  Pages:           frontend/src/pages/
  Components:      frontend/src/components/
  API client:      frontend/src/api/client.ts, types.ts
  Copy/strings:    frontend/src/strings.ts
  Theme:           frontend/src/theme/
```

Env config: repo-root `.env` (loaded by `backend/app/config.py` even when cwd is `backend/`).

## Current feature completeness

Phases 1–4 from `instructions.md` are largely implemented (vehicles, records, parts/stock, reminders, webhook, full UI). The main spec item still missing is the **cost reports** endpoint (`GET /reports/costs`). The README "Phase 1 only" note is stale.

Recent additions beyond the original spec:

- Service types CRUD (`/service-types`) and admin UI
- Fleet-wide records (`GET /records`) and reminders (`GET /reminders`) views
- Record change audit trail (`record_changes` table, migration `0003`)

## Suggested workflow for Claude

### Backend feature

1. Add/update Pydantic schema in `backend/app/schemas/`.
2. Add route in the appropriate `backend/app/api/` module; use `CurrentUser`, `get_db`, and `require_device_access` where needed.
3. Put non-trivial logic in `backend/app/services/` if it grows beyond a few lines.
4. Add pytest coverage in `backend/tests/` — follow `conftest.py` patterns (mocked Traccar via `respx`).
5. If schema changes: `alembic revision --autogenerate` (review carefully) or hand-write migration.

### Frontend feature

1. Add types to `frontend/src/api/types.ts`.
2. Add client methods to `frontend/src/api/client.ts`.
3. Build page/component under `frontend/src/pages/` or `components/`.
4. Add strings to `frontend/src/strings.ts` — do not hardcode user-visible text in JSX.
5. Wire route in `frontend/src/App.tsx` if new page; add nav item in `frontend/src/components/useAppMenu.tsx`.

### UI library

This project uses **MUI v6**, not Mantine (the spec said "pick one"). Use `@mui/material` components and the existing theme in `frontend/src/theme/`.

## Commands reference

```bash
# Tests (always run for backend changes)
cd backend && .venv/bin/python -m pytest

# Dev servers
cd backend && .venv/bin/uvicorn app.main:app --reload
cd frontend && npm run dev

# Migrations
cd backend && .venv/bin/alembic upgrade head

# Production build
docker compose build
docker compose run --rm backend alembic upgrade head
cd frontend && npm ci && npm run build
```

## Do not

- Add uvicorn `--workers` (breaks scheduler + caches).
- Grant the DB user access outside `track_maintenance`.
- Store stock levels as a mutable column (ledger is source of truth).
- Use `TRACCAR_ADMIN_TOKEN` for per-user authorization.
- Commit `.env` (secrets).
- Widen scope with unrelated refactors — keep diffs focused.

## When stuck

| Symptom | Check |
|---------|-------|
| 502 on `/auth/me` | Traccar down or unreachable at `TRACCAR_URL` |
| 401 after login | Cookie `secure` flag vs HTTP dev; `SESSION_COOKIE_SECURE` in `.env` |
| DB errors | `DATABASE_URL`, migrations applied (`alembic upgrade head`) |
| CORS in dev | Add `http://localhost:5173` to `CORS_ORIGINS`, or use Vite proxy |
| Tests pass, dev fails | Dev needs real MySQL + Traccar; tests use mocks |

For deployment and host setup details, see [README.md](README.md).
