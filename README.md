# Track Maintenance

Open-source companion service for [Traccar](https://www.traccar.org/) GPS fleet tracking. Adds vehicle maintenance logs, spare-parts inventory, service reminders, and cost reports — without modifying Traccar itself. All integration uses Traccar's REST API and `event.forward` webhooks.

**License:** [Apache License 2.0](LICENSE) (same as Traccar).

![Track Maintenance web app — Service types page](image-from-web-app.png)

## Features

- Maintenance records with odometer tracking and parts usage
- Spare-parts inventory with an append-only stock ledger
- Service reminders synced with Traccar maintenance entities
- Fleet-wide views, CSV export, cost reports, and dashboard
- Multi-tenant auth via Traccar credentials (session cookie or API token)
- **Live demo** — static playground on GitHub Pages (no backend required)
- **White-label ready** — custom app title, logo, favicon, and primary color at build time

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic |
| Frontend | React 18, TypeScript, Vite, MUI, TanStack Query |
| Database | MySQL 8, dedicated `track_maintenance` schema |
| Deploy | Docker backend (host networking) + static frontend on Nginx |

## Requirements

- A running [Traccar](https://www.traccar.org/) server (5.x+)
- MySQL 8 on the same host (or reachable from the backend)
- Nginx (or similar) for serving the frontend and proxying `/api/`

## Live demo

A fully interactive demo runs on GitHub Pages with seeded fleet data. No Traccar or MySQL needed — the frontend uses an in-memory mock API.

**URL:** [marvinjon.github.io/track-maintenance](https://marvinjon.github.io/track-maintenance/) (after you enable GitHub Pages; see below)

Changes persist in the browser session until you refresh or click **Reset demo**. Every push to the **`demo` branch** rebuilds and redeploys automatically via [.github/workflows/demo.yml](.github/workflows/demo.yml).

The mock API and demo UI live only on the `demo` branch — `main` stays production-only.

### Enable GitHub Pages (one-time)

1. Repo **Settings → Pages**
2. **Build and deployment → Source:** GitHub Actions
3. Push to the `demo` branch (or run the **Deploy demo** workflow manually)

If you fork the repo under a different name, update `VITE_BASE_PATH` in `.github/workflows/demo.yml` on the `demo` branch to `/<your-repo-name>/`.

### Keep demo in sync with main

When `main` gets new features, merge them into `demo`:

```bash
git checkout demo
git merge main
git push
```

Resolve any conflicts by keeping demo-specific files (`frontend/src/demo/`, demo hooks in `client.ts`, etc.).

### Run the demo locally

```bash
cd frontend
npm install
npm run dev:demo
```

Open [http://localhost:5173](http://localhost:5173). Build the static demo bundle with `npm run build:demo`.

| Variable | Purpose |
|----------|---------|
| `VITE_DEMO_MODE` | `true` swaps the API client for the in-memory mock |
| `VITE_BASE_PATH` | Asset base path (e.g. `/track-maintenance/` for GitHub Pages project sites) |

## Quick start (production)

### 1. MySQL schema

```sql
CREATE DATABASE track_maintenance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'maint_user'@'localhost' IDENTIFIED BY '***';
GRANT ALL PRIVILEGES ON track_maintenance.* TO 'maint_user'@'localhost';
FLUSH PRIVILEGES;
```

Grant only on `track_maintenance` — never on Traccar's schema.

### 2. Event forwarding

Add to Traccar's `traccar.xml`:

```xml
<entry key='event.forward.enable'>true</entry>
<entry key='event.forward.url'>http://127.0.0.1:8000/api/v1/webhooks/traccar?secret=***</entry>
```

Use the same secret as `WEBHOOK_SECRET` in `.env` (`openssl rand -hex 32`).

### 3. Environment

```bash
cp .env.example .env
# Fill in DATABASE_URL, WEBHOOK_SECRET, CORS_ORIGINS, APP_ENV=production
chmod 600 .env
```

### 4. Deploy

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

## Upgrading an existing deployment

From the repo root on the production host:

1. **Pull** the new release (`git pull` or unpack the new tarball).
2. **Review** `.env.example` for any new variables; update `.env` if needed (do not overwrite secrets).
3. **Backend** — rebuild, migrate, restart:
   ```bash
   docker compose build
   docker compose run --rm backend alembic upgrade head
   docker compose up -d
   ```
   Migrations are **not** run on container start; `alembic upgrade head` is required after every release that adds schema changes.
4. **Frontend** — rebuild and copy static files to the Nginx docroot:
   ```bash
   cd frontend
   npm ci
   npm run build
   sudo cp -r dist/* /var/www/fleet/
   ```
   If you use white-label env vars, source `frontend/.env.branding` before `npm run build` (see [White-labeling](#white-labeling)).
5. **Verify** — `curl -s http://127.0.0.1:8000/api/v1/health` should report database and Traccar OK; reload Nginx if you changed its config (`sudo nginx -t && sudo systemctl reload nginx`).

Traccar itself does not need to be restarted for Track Maintenance upgrades.

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
| `VITE_LOGIN_SUBTITLE` | Login screen subtitle |
| `VITE_PLATFORM_NAME` | GPS platform name in UI copy (defaults to `Traccar` when unset) |
| `VITE_DEFAULT_CURRENCY` | Default currency for new users (3-letter code, e.g. `ISK`; defaults to `USD`) |
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
| `WEBHOOK_SECRET` | Shared secret for Traccar event forwarding |
| `BIND_HOST` / `BIND_PORT` | Uvicorn bind address (`127.0.0.1:8000` in production) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `SESSION_COOKIE_SECURE` | `true` when served over HTTPS |

Full list: [.env.example](.env.example).

## Traccar integration

- **Auth:** Users sign in with Traccar email/password. The backend validates against Traccar and issues a `maint_session` cookie.
- **Devices:** Vehicle visibility matches Traccar — user A never sees user B's devices.
- **Reminders:** Traccar maintenance schedules are pulled on demand and in the background when each user logs in or restores their session. Traccar-linked reminders are read-only in this app; local-only reminders are also supported.
- **Odometer & maintenance:** Refreshed in the background when each user logs in or restores their session (and on demand per vehicle).
- **Webhooks:** Traccar `event.forward` marks reminders overdue; the webhook must stay localhost-only (Nginx returns 403 externally).

## Development

Local dev needs **Traccar** for login and device data. **MySQL starts automatically** via Docker — you do not need a local MySQL install for development.

### Quick start (recommended)

```bash
cp .env.dev.example .env   # first time only
./scripts/dev.sh           # starts MySQL, runs migrations, backend + frontend
```

Open `http://localhost:5173`. API docs at `http://127.0.0.1:8000/docs`.

### Database only

If you prefer separate terminals:

```bash
./scripts/dev-db.sh migrate   # start MySQL on :3307 and apply migrations

# Terminal 1 — backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```

MySQL runs in Docker on **`127.0.0.1:3307`** (port 3307 avoids clashing with native MySQL or SSH forwards on 3306). Data persists in a Docker volume between restarts.

```bash
./scripts/dev-db.sh down      # stop MySQL
./scripts/dev-db.sh status    # container status
```

### Tests

Pytest mocks Traccar and uses in-memory SQLite — no Docker required:

```bash
cd backend && .venv/bin/python -m pytest
```

### Traccar for local dev

Auth and device visibility call a real Traccar instance at `TRACCAR_URL`. If Traccar runs on a remote host, forward it first:

```bash
ssh -N -L 8082:127.0.0.1:8082 user@your-server
```

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
| DB errors | Wrong `DATABASE_URL` or migrations not applied — run `./scripts/dev-db.sh migrate` |
| CORS in dev | Add `http://localhost:5173` to `CORS_ORIGINS`, or use Vite proxy |

## Project status

Vehicles, maintenance records, parts inventory, reminders with Traccar mirroring, webhooks, odometer sync, cost reports, dashboard, and CSV import/export are implemented.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
