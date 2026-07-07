import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    auth,
    health,
    parts,
    records,
    reminders,
    reports,
    service_types,
    stock,
    vehicles,
    webhooks,
)
from app.config import get_settings, validate_production_settings
from app.services.maintenance_sync import run_scheduled_maintenance_sync
from app.services.notifications import run_scheduled_notifications
from app.services.odometer_sync import run_scheduled_sync
from app.services.traccar import TraccarUnavailable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ODOMETER_SYNC_INTERVAL_MINUTES = 30


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    validate_production_settings(settings)
    if settings.is_production:
        logger.info("Running in production mode (OpenAPI docs disabled)")

    # In-process scheduler — the reason this app must run as a single
    # process (see backend/Dockerfile).
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scheduled_sync,
        "interval",
        minutes=ODOMETER_SYNC_INTERVAL_MINUTES,
        id="odometer_sync",
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        run_scheduled_maintenance_sync,
        "interval",
        minutes=ODOMETER_SYNC_INTERVAL_MINUTES,
        id="maintenance_sync",
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        run_scheduled_notifications,
        "interval",
        minutes=ODOMETER_SYNC_INTERVAL_MINUTES,
        id="maintenance_notifications",
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "Odometer, maintenance sync, and notifications scheduled every %d minutes",
        ODOMETER_SYNC_INTERVAL_MINUTES,
    )
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()

    docs_kwargs: dict = {}
    if settings.is_production:
        docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}

    app = FastAPI(
        title="Track Maintenance",
        description="Vehicle maintenance & parts inventory companion for Traccar",
        version="0.2.0",
        lifespan=lifespan,
        **docs_kwargs,
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(TraccarUnavailable)
    async def traccar_unavailable_handler(
        request: Request, exc: TraccarUnavailable
    ) -> JSONResponse:
        logger.error("Traccar unavailable: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"detail": "Traccar is unavailable right now, please try again shortly."},
        )

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth.router)
    api_v1.include_router(health.router)
    api_v1.include_router(vehicles.router)
    api_v1.include_router(records.router)
    api_v1.include_router(service_types.router)
    api_v1.include_router(parts.router)
    api_v1.include_router(stock.router)
    api_v1.include_router(reminders.router)
    api_v1.include_router(reports.router)
    api_v1.include_router(webhooks.router)
    app.include_router(api_v1)

    return app


app = create_app()
