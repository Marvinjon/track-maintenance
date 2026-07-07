import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.schemas.health import AppConfigResponse, HealthResponse
from app.services.traccar import TraccarService, get_traccar

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def _public_traccar_url() -> str | None:
    url = get_settings().traccar_public_url.strip()
    return url or None


@router.get("/health", response_model=HealthResponse)
async def health(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> HealthResponse:
    """Used by the Docker HEALTHCHECK. DB connectivity is required (503 if down);
    Traccar reachability is informational only."""
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: database unreachable")
        database_ok = False

    traccar_reachable = await traccar.as_admin().ping()

    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if database_ok else "error",
        database=database_ok,
        traccar_reachable=traccar_reachable,
        traccar_public_url=_public_traccar_url(),
    )


@router.get("/config", response_model=AppConfigResponse)
async def app_config() -> AppConfigResponse:
    """Public app configuration for the frontend (no auth required)."""
    return AppConfigResponse(traccar_public_url=_public_traccar_url())
