# ---------------------------------------------------------------------------
# Builder: install dependencies into a self-contained venv.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# ---------------------------------------------------------------------------
# Final image: clean base + venv + app code only. Runs as non-root.
#
# IMPORTANT: this service must run as a SINGLE process (no --workers > 1).
# APScheduler runs in-process (odometer sync, from Phase 2 on); multiple
# workers would run the scheduler multiple times. The in-memory auth caches
# also assume one process.
#
# Migrations are NOT run on start. Run them deliberately as a one-off:
#   docker compose run --rm backend alembic upgrade head
# ---------------------------------------------------------------------------
FROM python:3.12-slim

RUN useradd -r appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic.ini ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

# The health endpoint returns 503 when the database is unreachable, which
# urlopen surfaces as an error -> healthcheck failure.
HEALTHCHECK --interval=30s --timeout=6s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('BIND_PORT', '8000')}/api/v1/health\", timeout=5)"]

# CMD (not ENTRYPOINT) so one-off commands can replace it, e.g. the migration:
#   docker compose run --rm backend alembic upgrade head
# sh -c so BIND_HOST/BIND_PORT env vars are expanded; exec keeps uvicorn as PID 1.
CMD ["sh", "-c", "exec uvicorn app.main:app --host ${BIND_HOST:-127.0.0.1} --port ${BIND_PORT:-8000}"]
