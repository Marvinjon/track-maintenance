# Track Maintenance

Open-source companion service for [Traccar](https://www.traccar.org/) GPS fleet tracking. Adds vehicle maintenance logs, spare-parts inventory, service reminders, and cost reports — without modifying Traccar itself. All integration uses Traccar's REST API and `event.forward` webhooks.

**License:** [Apache License 2.0](LICENSE) (same as Traccar).

## Features

- Maintenance records with odometer tracking and parts usage
- Spare-parts inventory with an append-only stock ledger
- Service reminders synced with Traccar maintenance entities
- Fleet-wide views, CSV export, cost reports, and dashboard
- Multi-tenant auth via Traccar credentials (session cookie or API token)
- **White-label ready** — custom app title, logo, favicon, and primary color at build time

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, APScheduler |
| Frontend | React 18, TypeScript, Vite, MUI, TanStack Query |
| Database | MySQL 8, dedicated `track_maintenance` schema |
| Deploy | Docker backend (host networking) + static frontend on Nginx |

## Requirements

- A running [Traccar](https://www.traccar.org/) server (5.x+)
- MySQL 8 on the same host (or reachable from the backend)
- Nginx (or similar) for serving the frontend and proxying `/api/`

## Quick start (production)

### 1. MySQL schema

```sql
CREATE DATABASE track_maintenance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'maint_user'@'localhost' IDENTIFIED BY '***';
GRANT ALL PRIVILEGES ON track_maintenance.* TO 'maint_user'@'localhost';
FLUSH PRIVILEGES;
```

Grant only on `track_maintenance` — never on Traccar's schema.

### 2. Traccar admin token

1. Log in to Traccar as an administrator.
2. Account settings → generate an API token.
3. Set `TRACCAR_ADMIN_TOKEN` in `.env` (background jobs only — not for user auth).

### 3. Event forwarding

Add to Traccar's `traccar.xml`:

```xml
<entry key='event.forward.enable'>true</entry>
<entry key='event.forward.url'>http://127.0.0.1:8000/api/v1/webhooks/traccar?secret=***</entry>
```

Use the same secret as `WEBHOOK_SECRET` in `.env` (`openssl rand -hex 32`).

### 4. Environment

```bash
cp .env.example .env
# Fill in DATABASE_URL, TRACCAR_ADMIN_TOKEN, WEBHOOK_SECRET, CORS_ORIGINS, APP_ENV=production
chmod 600 .env
```

### 5. Deploy

**Backend:**

```bash
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

**Frontend:**

```bash
cd frontend
npm ci
npm run build
sudo mkdir -p /var/www/fleet
sudo cp -r dist/* /var/www/fleet/
```

Install the vhost from [deploy/nginx.conf.example](deploy/nginx.conf.example) and reload Nginx.

Both backend and frontend must be deployed on upgrades — rebuilding Docker does not update static files.

## White-labeling

Customize branding without forking by setting Vite env vars at build time:

```bash
cp frontend/.env.branding.example frontend/.env.branding
# Edit VITE_APP_TITLE, VITE_LOGO_URL, VITE_PRIMARY_COLOR, etc.
cp your-logo.svg frontend/public/branding/logo.svg

cd frontend
set -a && source .env.branding && set +a && npm run build
```

| Variable | Purpose |
|----------|---------|
| `VITE_APP_TITLE` | App name (shown when no logo is set) |
| `VITE_LOGO_URL` | Logo path under `public/` (e.g. `/branding/logo.svg`) |
| `VITE_LOGO_ALT` | Logo alt text |
| `VITE_FAVICON_URL` | Favicon path (default `/favicon.svg`) |
| `VITE_PRIMARY_COLOR` | Primary theme color (hex, e.g. `#1a237e`) |

See [frontend/public/branding/logo.svg.example](frontend/public/branding/logo.svg.example) for a starter template.

For Traccar deep links ("View in Traccar"), set `TRACCAR_PUBLIC_URL` in the backend `.env` (e.g. `https://gps.example.com`).

## Environment variables

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | Set to `production` on live hosts (disables `/docs`, enables validation) |
| `DATABASE_URL` | e.g. `mysql+pymysql://maint_user:***@127.0.0.1:3306/track_maintenance` |
| `TRACCAR_URL` | Internal Traccar URL, usually `http://127.0.0.1:8082` |
| `TRACCAR_PUBLIC_URL` | User-facing Traccar URL for deep links (optional) |
| `TRACCAR_ADMIN_TOKEN` | Admin token for background sync jobs only |
| `WEBHOOK_SECRET` | Shared secret for Traccar event forwarding |
| `BIND_HOST` / `BIND_PORT` | Uvicorn bind address (`127.0.0.1:8000` in production) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `SESSION_COOKIE_SECURE` | `true` when served over HTTPS |

Full list: [.env.example](.env.example).

## Traccar integration

- **Auth:** Users sign in with Traccar email/password. The backend validates against Traccar and issues a `maint_session` cookie.
- **Devices:** Vehicle visibility matches Traccar — user A never sees user B's devices.
- **Reminders:** Traccar maintenance schedules are pulled every 30 minutes (and on demand). Traccar-linked reminders are read-only in this app; local-only reminders are also supported.
- **Odometer:** Pulled from Traccar on a schedule and on demand.
- **Webhooks:** Traccar `event.forward` marks reminders overdue; the webhook must stay localhost-only (Nginx returns 403 externally).

## Development

Local dev requires real MySQL and Traccar. Tests mock both.

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest
.venv/bin/uvicorn app.main:app --reload

# Frontend (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API docs at `http://127.0.0.1:8000/docs` (non-production).

See [CONTRIBUTING.md](CONTRIBUTING.md) for PR guidelines.

## Production security checklist

- [ ] `APP_ENV=production` and `SESSION_COOKIE_SECURE=true`
- [ ] `CORS_ORIGINS` set to exact fleet origin (no wildcard)
- [ ] `WEBHOOK_SECRET` is 32+ random bytes
- [ ] `.env` permissions `chmod 600`
- [ ] Nginx blocks `/api/v1/webhooks/` from the public internet
- [ ] MySQL user scoped to `track_maintenance.*` only
- [ ] Migrations applied; `GET /api/v1/health` healthy

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `502` on `/auth/me` | Traccar down or wrong `TRACCAR_URL` |
| `401` after login | Cookie `secure` flag vs HTTP dev; check `SESSION_COOKIE_SECURE` |
| DB errors | Wrong `DATABASE_URL` or migrations not applied |
| CORS in dev | Add `http://localhost:5173` to `CORS_ORIGINS`, or use Vite proxy |

## Project status

Vehicles, maintenance records, parts inventory, reminders with Traccar mirroring, webhooks, odometer sync, cost reports, dashboard, and CSV import/export are implemented.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
