# Agent guide — Track Maintenance

This file gives coding agents a fast, accurate map of the repository. For deployment and host setup, see [README.md](README.md). For the original product spec and build phases, see [instructions.md](instructions.md).

## What this project is

A **standalone companion service** for an existing [Traccar](https://www.traccar.org/) GPS fleet-tracking deployment. It adds:

- Vehicle maintenance logs (service records, odometer tracking)
- Spare-parts inventory with a stock-movement ledger
- Service reminders mirrored to Traccar maintenance entities

**Hard constraints (never violate):**

- Do **not** write to Traccar's database or join across schemas in SQL.
- Reference Traccar devices only by numeric `traccar_device_id`; fetch live device data via Traccar's REST API.
- User-facing authorization always uses the **caller's** Traccar credentials (session or bearer token). All Traccar API reads and writes use the authenticated user's credential.
- Multi-tenancy must match Traccar: user A must never see or modify user B's devices.

## Tech stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, httpx |
| Database | MySQL 8, schema `track_maintenance` (separate user, grants only on this schema) |
| Frontend | React 18, TypeScript, Vite, TanStack Query, **MUI** (Material UI), react-router-dom |
| Deploy | Docker backend (`network_mode: host`), static frontend on host Nginx |
| Tests | pytest (backend, mocked Traccar + in-memory SQLite) |

## Repository layout

```
track-maintenance/
├── agents.md              ← this file
├── claude.md              ← Claude-specific workflow notes
├── instructions.md        ← original spec & build phases
├── README.md              ← deployment, env vars, dev setup
├── .env.example           ← template for repo-root .env
├── docker-compose.yml     ← production backend only
├── deploy/
│   └── nginx.conf.example # host Nginx vhost
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app, router wiring
│   │   ├── config.py      # pydantic-settings (loads repo-root .env)
│   │   ├── db.py          # SQLAlchemy engine + get_db dependency
│   │   ├── models/        # ORM models
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── api/           # route handlers + deps.py (auth)
│   │   ├── services/      # Traccar client, odometer sync, reminders, stock, audit
│   │   └── alembic/       # migrations (versions/)
│   ├── tests/             # pytest suite
│   ├── Dockerfile
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── api/           # typed REST client (client.ts, types.ts)
    │   ├── pages/         # route-level screens
    │   ├── components/    # shared UI (drawers, modals, layout)
    │   ├── theme/         # MUI theme tokens
    │   ├── strings.ts     # all user-visible English copy (i18n-ready)
    │   └── App.tsx        # auth gate + react-router routes
    ├── vite.config.ts     # dev proxy: /api → 127.0.0.1:8000
    └── package.json
```

## Implementation status

The README still mentions "Phase 1 only"; the codebase has moved well beyond that:

| Area | Status |
|------|--------|
| Auth (login, `maint_session` cookie, bearer support) | Done |
| Vehicles CRUD, odometer sync (endpoint + per-user background sync) | Done |
| Maintenance records CRUD + change audit (`record_changes`) | Done |
| Service types CRUD | Done |
| Parts, stock movements, low-stock | Done |
| Record ↔ parts linkage with atomic stock decrement | Done |
| Reminders + Traccar mirroring + webhook handler | Done |
| Frontend pages (vehicles, detail, parts, low stock, reminders, services) | Done |
| Reports (`GET /reports/costs`) | Not implemented (spec phase 4 stub) |

Alembic migrations: `0001` through `0011` (see `backend/app/alembic/versions/`).

## Backend architecture

### Entry point

`backend/app/main.py` — mounts all routers under `/api/v1`, configures CORS, handles `TraccarUnavailable` → 502.

**Important:** run as a **single uvicorn process** (no workers). In-memory auth caches assume one process.

### API routes (`backend/app/api/`)

All paths are prefixed with `/api/v1`.

| Module | Prefix | Purpose |
|--------|--------|---------|
| `auth.py` | `/auth` | `POST /login`, `GET /me`, `POST /logout` |
| `health.py` | `/health` | DB + Traccar reachability |
| `vehicles.py` | `/vehicles` | List/create/detail/patch/archive, `POST /{id}/sync-odometer` |
| `records.py` | `/records`, `/vehicles/{id}/records` | Fleet-wide and per-vehicle maintenance records |
| `service_types.py` | `/service-types` | CRUD + records by service type |
| `parts.py` | `/parts` | CRUD, movements ledger |
| `stock.py` | `/stock` | `GET /low` |
| `reminders.py` | `/reminders`, `/vehicles/{id}/reminders` | CRUD with Traccar sync |
| `webhooks.py` | `/webhooks` | `POST /traccar` (secret-protected, localhost only in prod) |

OpenAPI docs: `http://127.0.0.1:8000/docs` when the backend is running.

### Auth (`backend/app/api/deps.py`)

- No local user accounts. Login (`POST /auth/login`) validates email/password against Traccar, then stores the Traccar session id in an HttpOnly `maint_session` cookie (separate domain from Traccar UI).
- Protected routes accept `maint_session` cookie **or** `Authorization: Bearer <traccar-api-token>`.
- Session validation is cached 60s; device visibility checks cached 5 min per user+device.
- `require_device_access(vehicle)` ensures the caller can see the Traccar device.

### Services (`backend/app/services/`)

| File | Role |
|------|------|
| `traccar.py` | httpx client: `as_user()`, unit conversions (m→km, ms→h) |
| `odometer_sync.py` | On-demand odometer/engine-hours pull; reminder status recompute |
| `user_sync.py` | Background odometer + maintenance pull after login/session restore |
| `maintenance_sync.py` | Pull Traccar maintenance schedules into local reminders |
| `reminders.py` | Local reminder helpers; push maintenance `start` to Traccar after service |
| `stock.py` | Stock level = `SUM(stock_movements.quantity)` |
| `record_audit.py` | Logs field-level changes on record updates |

### Models (`backend/app/models/`)

| Model | Table | Notes |
|-------|-------|-------|
| `Vehicle` | `vehicles` | Linked to Traccar via `traccar_device_id` |
| `ServiceType` | `service_types` | Seeded defaults in migration 0001 |
| `MaintenanceRecord` | `maintenance_records` | Service log entries |
| `RecordPart` | `record_parts` | Parts used in a service (triggers stock movement) |
| `RecordChange` | `record_changes` | Audit trail for record edits |
| `Part` | `parts` | Inventory catalog |
| `StockMovement` | `stock_movements` | Append-only ledger |
| `Reminder` | `reminders` | Local + optional `traccar_maintenance_id` |
| `WebhookEvent` | `webhook_events` | Raw Traccar event.forward payloads |

### Config (`backend/app/config.py`)

Loads `.env` from the **repo root** (works whether you start uvicorn from `backend/` or the root). See `.env.example` for all variables.

## Frontend architecture

### Routes (`frontend/src/App.tsx`)

| Path | Page |
|------|------|
| `/` | Vehicles list |
| `/vehicles/:vehicleId` | Vehicle detail (records, reminders tabs) |
| `/maintenance` | Upcoming maintenance (fleet reminders) |
| `/services` | Fleet-wide service records |
| `/service-types` | Service type management |
| `/parts` | Parts inventory |
| `/stock/low` | Low-stock alert view |
| `/settings` | App settings (theme, etc.) |

### Data layer

- `frontend/src/api/client.ts` — fetch wrapper, `credentials: "include"` for session cookie.
- `frontend/src/api/types.ts` — TypeScript types mirroring backend schemas.
- TanStack Query for caching; query key `["auth", "me"]` gates the app shell.

### UI conventions

- All user-visible strings live in `frontend/src/strings.ts` (English only; structured for future Icelandic).
- MUI components + custom theme in `frontend/src/theme/`.
- Formatting helpers in `frontend/src/format.ts`.

## Local development

Prerequisites: Traccar running (or SSH-forwarded). MySQL for local dev starts via `./scripts/dev-db.sh` (Docker on port 3307). Pytest mocks both and uses in-memory SQLite.

```bash
cp .env.dev.example .env   # first time
./scripts/dev.sh           # MySQL + migrations + backend + frontend
```

Or manually after `./scripts/dev-db.sh migrate`:

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to :8000
```

Add `http://localhost:5173` to `CORS_ORIGINS` in `.env` if calling the API without the Vite proxy.

Remote host: SSH-forward Traccar (8082) before starting the backend if not local.

## Testing

```bash
cd backend && .venv/bin/python -m pytest
```

Tests live in `backend/tests/`. Key coverage:

- Auth, session caching, bearer tokens (`test_auth.py`)
- Multi-tenant device visibility (`test_visibility.py`, scattered in CRUD tests)
- Records, parts, stock ledger invariants (`test_records.py`, `test_record_parts.py`, `test_parts.py`)
- Reminders + Traccar mirroring (`test_reminders.py`)
- Webhook secret + maintenance events (`test_webhook.py`)
- Traccar unit conversions (`test_traccar_units.py`)

Fixtures and Traccar mocks: `backend/tests/conftest.py`.

## Deployment (summary)

1. Fill repo-root `.env` from `.env.example`.
2. `docker compose build && docker compose run --rm backend alembic upgrade head && docker compose up -d`
3. Build frontend: `cd frontend && npm ci && npm run build`
4. Copy `frontend/dist/*` to host Nginx docroot (e.g. `/var/www/fleet/`).
5. Install `deploy/nginx.conf.example` — proxies `/api/` to backend, **blocks** `/api/v1/webhooks/` from the public internet.
6. Configure Traccar `event.forward` in `/opt/traccar/conf/traccar.xml` (see README).

Migrations are **never** auto-run on container start.

## Common agent pitfalls

1. **Do not add uvicorn workers** — breaks in-memory auth caches.
2. **Do not query Traccar's DB** — only REST API + webhooks.
3. **Always forward caller credentials** to Traccar for authorization and data access.
4. **Stock is derived** — never store a separate `current_stock` column; always `SUM(movements)`.
5. **Traccar units** — distance in meters, hours in milliseconds when talking to Traccar API; convert in `services/traccar.py`.
6. **Webhook route** — must stay reachable on localhost only; Nginx returns 403 externally.
7. **Frontend + backend deploy together** — rebuilding Docker does not update static files Nginx serves.
8. **Match existing style** — minimal diffs, MUI (not Mantine), strings in `strings.ts`.

## Files to read first for common tasks

| Task | Start here |
|------|------------|
| New API endpoint | `backend/app/api/deps.py`, similar route in `backend/app/api/`, schema in `backend/app/schemas/` |
| DB change | Model in `backend/app/models/`, new Alembic revision in `backend/app/alembic/versions/` |
| Traccar integration | `backend/app/services/traccar.py` |
| New UI page | `frontend/src/pages/`, wire route in `App.tsx`, API in `client.ts` + `types.ts` |
| User-visible text | `frontend/src/strings.ts` |
| Auth behavior | `backend/app/api/auth.py`, `backend/app/api/deps.py` |
| Background sync | `backend/app/services/user_sync.py`, `backend/app/api/auth.py` |
