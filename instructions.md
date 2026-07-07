# Project Spec: Traccar Maintenance & Parts Inventory Companion Service

You are building a **standalone companion service** for an existing Traccar GPS fleet-tracking deployment. It adds vehicle maintenance logs and spare-parts inventory. It must NOT modify Traccar itself in any way — no schema changes to Traccar's database, no patches to the Traccar backend. All integration happens through Traccar's REST API and its event-forwarding webhook.

Read this entire document, then produce an implementation plan broken into the phases described in "Build Phases". Ask clarifying questions before writing code if anything is ambiguous.

---

## 1. Context & Constraints

- Traccar (stock, latest 6.x) runs as a **native systemd service** on an Ubuntu server (`/opt/traccar`, config at `/opt/traccar/conf/traccar.xml`, managed via `systemctl`). It is NOT in Docker. MySQL runs natively on the same host. Nginx (native) reverse-proxies in front.
- This service is multi-tenant: Traccar users only see their own devices. Our service must enforce the exact same visibility — never leak vehicles between customers.
- Traccar must remain upgradeable at any time. Therefore:
  - **NEVER** write to Traccar's database tables.
  - **NEVER** join across schemas in SQL. Reference Traccar devices only by their numeric `deviceId`, and fetch live device data via the Traccar REST API.
  - The only Traccar coupling allowed: REST API calls + receiving `event.forward` webhooks.

## 2. Tech Stack (use exactly this)

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x (declarative, typed), Alembic for migrations, Pydantic v2 schemas, `httpx` for calling the Traccar API, `uvicorn` server.
- **Database:** MySQL 8, dedicated schema `track_maintenance` (same MySQL server as Traccar, separate schema, separate DB user with privileges ONLY on this schema).
- **Frontend:** React 18 + TypeScript + Vite, TanStack Query for data fetching, plain REST client. Simple, clean UI — tables and forms, no heavy design system needed (use Mantine or shadcn/ui, pick one and stay consistent).
- **Deployment:** the production deliverable is **Docker**: a production-grade multi-stage backend Dockerfile (non-root, healthcheck) and a `docker-compose.yml` using `network_mode: host` so the container reaches the native Traccar (127.0.0.1:8082) and MySQL (127.0.0.1:3306) on the same Ubuntu host — full details in Section 10. Frontend is a static Vite build served by the host's existing native Nginx (a frontend Dockerfile is a bonus, not required). Traccar and MySQL always already exist externally; connect via env vars, never create containers or units for them.
- **Testing:** pytest for backend (unit tests for stock-level calculation, auth dependency, webhook handler; integration tests with a test DB). Vitest optional for frontend, not required for MVP.

## 3. Repository Layout

```
maintenance-service/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py            # pydantic-settings, all env vars
│   │   ├── db.py                # engine, session dependency
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── api/
│   │   │   ├── deps.py          # auth dependency (Traccar session passthrough)
│   │   │   ├── vehicles.py
│   │   │   ├── records.py
│   │   │   ├── parts.py
│   │   │   ├── stock.py
│   │   │   └── webhooks.py      # Traccar event.forward receiver
│   │   ├── services/
│   │   │   ├── traccar.py       # Traccar API client (httpx)
│   │   │   ├── odometer_sync.py # background job
│   │   │   └── reminders.py     # manage Traccar maintenance entries via API
│   │   └── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/                 # typed API client
│   │   ├── pages/               # Vehicles, VehicleDetail, Parts, Stock, Records
│   │   └── components/
│   ├── Dockerfile
│   └── vite.config.ts
├── docker-compose.yml
├── .env.example
└── README.md
```

## 4. Authentication & Multi-Tenancy (critical — implement first)

Do NOT build local user accounts. Piggyback on Traccar sessions:

1. Frontend is served on the same parent domain as Traccar (e.g. `fleet.example.com` next to `gps.example.com`, or a subpath) so the Traccar `JSESSIONID` cookie is available; ALSO support an `Authorization: Bearer <traccar-api-token>` header for API clients.
2. Backend auth dependency (`api/deps.py`):
   - Take the incoming cookie or bearer token and forward it to `GET {TRACCAR_URL}/api/session`.
   - If Traccar returns 200, the JSON body is the authenticated Traccar user (`id`, `name`, `email`, `administrator`). Cache this validation in-memory for 60 seconds keyed by token/cookie hash to avoid hammering Traccar.
   - If Traccar returns 4xx, respond 401.
3. Device authorization: for any request touching a vehicle, verify the user can see that Traccar device by calling `GET {TRACCAR_URL}/api/devices?id=<deviceId>` **with the user's own credentials** (forwarded cookie/token). If Traccar returns it, they're authorized. Cache per user+device for 5 minutes.
4. The service itself holds ONE admin token (`TRACCAR_ADMIN_TOKEN` env var) used ONLY by background jobs (odometer sync, reminder management) — never for user-facing authorization decisions.

## 5. Database Schema (Alembic migration 0001)

All tables get `id BIGINT PK AUTO_INCREMENT`, `created_at`, `updated_at`.

**vehicles**
- `traccar_device_id BIGINT NOT NULL UNIQUE`
- `plate VARCHAR(20)`, `vin VARCHAR(32) NULL`, `make VARCHAR(64)`, `model VARCHAR(64)`, `year SMALLINT NULL`
- `odometer_km_cached DECIMAL(12,1) NULL`, `odometer_synced_at DATETIME NULL`
- `engine_hours_cached DECIMAL(12,1) NULL`
- `notes TEXT NULL`
- `archived BOOLEAN DEFAULT FALSE`

**service_types**
- `name VARCHAR(100) NOT NULL` (e.g., Oil change, Brake service, Tire change, Annual inspection)
- `default_interval_km INT NULL`, `default_interval_days INT NULL`
- Seed with 6–8 sensible defaults in the migration.

**maintenance_records**
- `vehicle_id FK vehicles`
- `service_type_id FK service_types`
- `performed_at DATE NOT NULL`
- `odometer_km DECIMAL(12,1) NULL` (prefilled from live Traccar odometer, editable)
- `cost DECIMAL(12,2) NULL`, `currency CHAR(3) DEFAULT 'ISK'`
- `performed_by VARCHAR(120) NULL` (free text: workshop name or person)
- `notes TEXT NULL`
- `created_by_traccar_user_id BIGINT NOT NULL`

**parts**
- `sku VARCHAR(64) UNIQUE NULL`, `name VARCHAR(150) NOT NULL`
- `unit VARCHAR(20) DEFAULT 'pcs'`
- `min_stock DECIMAL(12,2) DEFAULT 0`
- `unit_cost DECIMAL(12,2) NULL`
- `archived BOOLEAN DEFAULT FALSE`

**stock_movements** (append-only ledger — current stock is always SUM(quantity))
- `part_id FK parts`
- `quantity DECIMAL(12,2) NOT NULL` (positive = in, negative = out)
- `reason ENUM('purchase','used_in_service','adjustment','return') NOT NULL`
- `maintenance_record_id FK maintenance_records NULL`
- `note VARCHAR(255) NULL`
- `created_by_traccar_user_id BIGINT NOT NULL`

**record_parts**
- `maintenance_record_id FK`, `part_id FK`, `quantity DECIMAL(12,2) NOT NULL`
- Creating a row here MUST atomically create the matching negative `stock_movements` row (same DB transaction). Deleting/editing must reverse/adjust it.

**reminders**
- `vehicle_id FK`, `service_type_id FK`
- `traccar_maintenance_id BIGINT NULL` (id of the mirrored Traccar maintenance entity)
- `interval_km INT NULL`, `interval_days INT NULL`
- `last_service_odometer_km DECIMAL(12,1) NULL`, `last_service_date DATE NULL`
- `status ENUM('ok','due_soon','overdue') DEFAULT 'ok'`

**webhook_events** (raw audit log)
- `received_at DATETIME`, `event_type VARCHAR(64)`, `traccar_device_id BIGINT NULL`, `payload JSON`

## 6. Backend API Endpoints

All under `/api/v1`, all behind the auth dependency, all device-scoped per Section 4.

**Vehicles**
- `GET /vehicles` — list vehicles the current user may see. Implementation: fetch the user's devices from Traccar (`GET /api/devices` with user credentials), then return matching local `vehicles` rows; include devices with no local row yet as `{registered: false}` stubs so the UI can offer "enable maintenance tracking".
- `POST /vehicles` — create local vehicle row for a traccar_device_id (validate visibility).
- `GET /vehicles/{id}` — detail incl. cached odometer, open reminders, last 5 records.
- `PATCH /vehicles/{id}`, `DELETE` (soft archive).
- `POST /vehicles/{id}/sync-odometer` — on-demand pull from Traccar (latest position → `attributes.totalDistance` converted m→km; fall back to `attributes.odometer` if present; also read `attributes.hours` ms→h for engine hours).

**Maintenance records**
- `GET /vehicles/{id}/records` (paginated, newest first)
- `POST /vehicles/{id}/records` — body may include `parts: [{part_id, quantity}]`; create record + record_parts + stock movements in one transaction; if a linked reminder exists for that service type, reset it (update `last_service_*`, recompute status, and PUT the updated `start`/period to the Traccar maintenance entity via admin token).
- `PATCH /records/{id}`, `DELETE /records/{id}` (reverse stock movements on delete).

**Parts & stock**
- `GET /parts` — include computed `current_stock` (SUM of movements, single GROUP BY query) and `low_stock: current_stock < min_stock`.
- `POST /parts`, `PATCH /parts/{id}`, archive.
- `POST /parts/{id}/movements` — manual purchase/adjustment entries.
- `GET /parts/{id}/movements` — ledger view, paginated.
- `GET /stock/low` — all parts under min_stock.

**Reminders**
- `GET /vehicles/{id}/reminders`, `POST` (local-only), `PATCH`/`DELETE` (local-only; Traccar-linked rows are read-only).
- `POST /vehicles/{id}/sync-maintenance` — pull maintenance schedules from Traccar (admin token, `GET /api/maintenances?deviceId=`).
- Scheduled pull every 30 minutes for all non-archived vehicles. Upsert by `traccar_maintenance_id`; prune local Traccar-linked rows removed in Traccar.
- Logging a service resets matching reminders locally; if `traccar_maintenance_id` is set, also `PUT` the new `start` to Traccar.

**Webhook**
- `POST /webhooks/traccar` — receives Traccar `event.forward` JSON. Protect with a shared-secret query param or header (`WEBHOOK_SECRET` env var) since Traccar can't sign requests. Store raw payload in `webhook_events`. If `event.type == "maintenance"`, look up the vehicle by `event.deviceId` and set matching reminder status to `overdue`; optionally send notification email. Respond 200 fast; do processing inline (it's light) but never let an exception return 5xx repeatedly — log and return 200 after storing the raw event.

**Reports (phase 4, stub the routes)**
- `GET /reports/costs?from=&to=&vehicle_id=` — total cost per vehicle per month.

## 7. Traccar API Client (`services/traccar.py`)

Thin typed wrapper over httpx with two modes:
- `as_user(cookie_or_token)` — forwards user credentials (session validation, device visibility, device list).
- `as_admin()` — uses `TRACCAR_ADMIN_TOKEN` (Bearer) for: latest positions (`GET /api/positions?deviceId=`), maintenance list/update (`GET /api/maintenances?deviceId=`, `PUT /api/maintenances/{id}`), accumulators if needed.
- Timeouts 10s, one retry on connect errors, raise a clean `TraccarUnavailable` exception mapped to HTTP 502 with a friendly message.
- Unit conversions live here: Traccar totalDistance is meters, hours attribute is milliseconds. Expose km and hours only; convert back when writing maintenance entities.

## 8. Background Jobs

- **Odometer sync** (every 30 min): for all non-archived vehicles, fetch latest position via admin token, update `odometer_km_cached`, `engine_hours_cached`, `odometer_synced_at`. Recompute reminder statuses.
- **Maintenance pull** (every 30 min): sync Traccar maintenance schedules into local reminders.
- **Email notifications** (every 30 min, if SMTP configured): email Traccar users scoped to each vehicle (maintenance notifications with mail channel, or device access as fallback) when reminders are `due_soon` or `overdue`, with per-recipient `NOTIFICATION_COOLDOWN_HOURS` deduplication.
- Make thresholds configurable via env (`DUE_SOON_KM=500`, `DUE_SOON_DAYS=14`).

## 9. Frontend Pages (MVP)

1. **Vehicles list** — table: plate, make/model, odometer (with sync age tooltip), reminder status badge (green/yellow/red), last service date. Row click → detail. Button on unregistered Traccar devices: "Enable maintenance tracking".
2. **Vehicle detail** — header with live odometer + "Sync now"; tabs: Records (table + "Log service" modal), Reminders (list + create form with interval km/days).
3. **Log service modal** — service type select, date (default today), odometer (prefilled from cache, editable), cost, performed by, notes, and a parts picker (searchable select + quantity, multiple rows) showing current stock next to each part and warning if quantity > stock (allow it, stock can go negative, just warn).
4. **Parts & inventory** — parts table with current stock and low-stock highlighting; part detail drawer with movement ledger and "Add purchase/adjustment" form.
5. **Low stock** — simple filtered view, linked from a badge in the nav.

Keep the UI in English with all strings in one `strings.ts` file so Icelandic translation can be added later.

## 10. Configuration & Deployment (Docker, production-ready — PRIMARY DELIVERABLE)

The production deliverable is a **Docker deployment**: a production-grade backend image, a frontend built to static files, and a `docker-compose.yml` that runs on the existing Ubuntu host next to the native (non-Docker) Traccar and MySQL. No systemd units, no venvs on the host.

### .env.example

```
# Host networking: Traccar and MySQL are native services on the same host,
# reachable on localhost from inside the backend container.
DATABASE_URL=mysql+pymysql://maint_user:***@127.0.0.1:3306/track_maintenance
TRACCAR_URL=http://127.0.0.1:8082
TRACCAR_ADMIN_TOKEN=***
WEBHOOK_SECRET=***
BIND_HOST=127.0.0.1
BIND_PORT=8000
DUE_SOON_KM=500
DUE_SOON_DAYS=14
CORS_ORIGINS=https://fleet.example.com
```

### 10a. Backend image (production-grade Dockerfile)

Requirements for `backend/Dockerfile`:

- Multi-stage build: builder stage installs dependencies into a venv (`python:3.12-slim` base, `pip install --no-cache-dir`), final stage copies only the venv + app code onto a clean `python:3.12-slim`.
- Runs as a non-root user (`useradd -r appuser`), `USER appuser`.
- `ENTRYPOINT` runs uvicorn directly: `uvicorn app.main:app --host ${BIND_HOST} --port ${BIND_PORT}` (single process is fine — APScheduler runs in-process, so do NOT use multiple workers; document this constraint in the Dockerfile comments).
- Migrations are NOT run automatically on container start. Provide them as an explicit one-off command documented in the README: `docker compose run --rm backend alembic upgrade head`. This keeps upgrades deliberate and safe.
- `HEALTHCHECK` hitting a `GET /api/v1/health` endpoint (implement it: returns 200 + DB connectivity check + Traccar reachability as informational fields).
- Image must be self-contained: no bind-mounting source code in production; compose mounts only the `.env` file.

### 10b. Frontend

- Multi-stage `frontend/Dockerfile`: `node:22-slim` build stage (`npm ci && npm run build`), final stage `nginx:alpine` serving `dist/` — OR (simpler, preferred) skip a frontend container entirely and document copying `dist/` to the host for the existing native Nginx to serve. Implement the containerless option as primary; keep the Dockerfile as a bonus.

### 10c. docker-compose.yml (production)

```yaml
services:
  backend:
    image: maintenance-backend:latest
    build: ./backend
    network_mode: host        # Traccar (8082) and MySQL (3306) are native
                              # services bound to 127.0.0.1 on this host.
                              # Host networking lets the container use them
                              # directly, and uvicorn on 127.0.0.1:8000 stays
                              # unreachable from outside — Nginx proxies to it.
    env_file: .env
    restart: unless-stopped
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
```

Rationale (include as comments): the host's MySQL binds only to `127.0.0.1`, so bridge networking would require reconfiguring MySQL's bind-address and adding a `'maint_user'@'172.%'` grant. `network_mode: host` avoids touching MySQL/Traccar config entirely and keeps the backend bound to loopback. Document the bridge alternative (`extra_hosts: ["host.docker.internal:host-gateway"]` + MySQL bind/grant changes) in the README as a fallback for hosts where host networking is unacceptable.

Production upgrade flow to document in README: `git pull && docker compose build && docker compose run --rm backend alembic upgrade head && docker compose up -d`.

### 10d. Nginx (native, on the host — provide `deploy/nginx.conf.example`)

- Serve frontend static files (from `dist/` copied to e.g. `/var/www/fleet/`).
- Proxy `/api/` → `http://127.0.0.1:8000`.
- `location /api/v1/webhooks/ { return 403; }` — the webhook must never be reachable through the public vhost (Traccar posts to it directly on localhost).
- README note: the frontend must be served on the same registrable domain as the Traccar web UI so the Traccar session cookie is sent (e.g. `fleet.example.com` next to `gps.example.com`, cookie scoped accordingly, or a subpath on the same host).

### Traccar-side configuration (manual, one-time — config, not a patch, survives upgrades)

Add to `/opt/traccar/conf/traccar.xml`, then `sudo systemctl restart traccar`:

```xml
<entry key='event.forward.enable'>true</entry>
<entry key='event.forward.url'>http://127.0.0.1:8000/api/v1/webhooks/traccar?secret=***</entry>
```

With host networking the backend listens on the host's loopback, so native Traccar reaches it at `127.0.0.1:8000` with no extra wiring.

### MySQL setup (manual, one-time — document in README)

```sql
CREATE DATABASE track_maintenance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'maint_user'@'localhost' IDENTIFIED BY '***';
GRANT ALL PRIVILEGES ON track_maintenance.* TO 'maint_user'@'localhost';
FLUSH PRIVILEGES;
```

(`'localhost'` is correct here because with host networking the container connects via the host loopback.) No grants on any other schema — this is deliberate and must not be widened.

## 11. Build Phases (implement in this order, working software after each)

- **Phase 1 — Skeleton + Auth:** repo layout, config, DB + migration 0001, Traccar client, auth dependency with session passthrough and device-visibility check, `GET /vehicles` end-to-end, health endpoint, production backend Dockerfile + docker-compose.yml (host networking) + Nginx snippet. Tests: auth dependency (mock Traccar), visibility enforcement.
- **Phase 2 — Maintenance log:** vehicles CRUD, odometer sync (endpoint + scheduler), records CRUD, frontend pages 1–3 minus parts picker. Tests: record CRUD, odometer unit conversion.
- **Phase 3 — Inventory:** parts, movements ledger, record_parts with atomic stock decrement, frontend pages 4–5 + parts picker in the modal. Tests: stock = SUM invariant, transactional rollback when record creation fails mid-way.
- **Phase 4 — Reminders + webhook:** reminders CRUD with Traccar mirroring, webhook receiver, status recomputation, badges in UI. Tests: webhook secret rejection, maintenance event → overdue transition, reminder reset on service logging.

## 12. Non-Goals (do NOT build)

- No local user management, roles, or registration.
- No modifications to Traccar source or its DB schema.
- No file/photo uploads in MVP.
- No work-order assignment/workflow.
- No i18n framework yet (single strings file only).

## 13. Definition of Done per Phase

- Docker path works end-to-end: `docker compose build`, `docker compose run --rm backend alembic upgrade head`, `docker compose up -d` gives a healthy backend (passing HEALTHCHECK) on `127.0.0.1:8000` talking to the existing native Traccar + MySQL via host networking.
- Backend image runs as non-root, is multi-stage, and contains no source bind-mounts in production compose.
- All endpoints have Pydantic response models and appear correctly in `/docs` (OpenAPI).
- Multi-tenancy test passes: user A cannot read/write vehicles for devices only visible to user B.
- No SQL touches any table outside the `track_maintenance` schema (verify: the DB user literally has no grants elsewhere).
- Webhook route is blocked at Nginx level for external requests (403) while reachable from localhost.
- README covers: Docker build/upgrade flow, env vars, MySQL user creation, frontend build + copy to Nginx, the two Traccar config entries, how to create the Traccar admin token, and the bridge-networking fallback.