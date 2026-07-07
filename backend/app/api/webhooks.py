"""Traccar event.forward receiver.

Not behind the user auth dependency: Traccar can't authenticate as a user, so
the route is protected by a shared secret (query param or header) and is
additionally blocked at the Nginx level for external requests — Traccar posts
to it directly on localhost.

Contract with Traccar: respond 200 fast and never repeatedly 5xx — the raw
event is stored first, processing failures are logged and swallowed.
"""

import hmac
import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Reminder, ReminderStatus, Vehicle, WebhookEvent
from app.services.notifications import notify_reminders_for_vehicle
from app.services.vehicles import active_vehicle_for_device

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _check_secret(request: Request) -> None:
    expected = get_settings().webhook_secret
    provided = request.query_params.get("secret") or request.headers.get(
        "X-Webhook-Secret", ""
    )
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _extract_event(payload: dict[str, Any]) -> tuple[str | None, int | None, int | None]:
    """Returns (event_type, device_id, maintenance_id) from a forwarded payload."""
    event = payload.get("event", {}) if isinstance(payload.get("event"), dict) else {}
    event_type = event.get("type") or payload.get("type")
    device_id = event.get("deviceId")
    if device_id is None:
        device = payload.get("device")
        if isinstance(device, dict):
            device_id = device.get("id")
    maintenance_id = event.get("maintenanceId")
    if maintenance_id is None:
        maintenance = payload.get("maintenance")
        if isinstance(maintenance, dict):
            maintenance_id = maintenance.get("id")
    return event_type, device_id, maintenance_id


def _mark_reminders_overdue(
    db: Session, device_id: int, maintenance_id: int | None
) -> tuple[Vehicle | None, list[int]]:
    vehicle = active_vehicle_for_device(db, device_id)
    if vehicle is None:
        return None, []
    query = select(Reminder).where(Reminder.vehicle_id == vehicle.id)
    if maintenance_id is not None:
        query = query.where(Reminder.traccar_maintenance_id == maintenance_id)
    updated_ids: list[int] = []
    for reminder in db.execute(query).scalars():
        reminder.status = ReminderStatus.overdue
        updated_ids.append(reminder.id)
    return vehicle, updated_ids


@router.post("/traccar", status_code=status.HTTP_200_OK)
async def receive_traccar_event(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    _check_secret(request)

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {"raw": payload}
    except Exception:
        payload = None

    event_type, device_id, maintenance_id = (
        _extract_event(payload) if payload else (None, None, None)
    )

    try:
        db.add(
            WebhookEvent(
                received_at=datetime.now(timezone.utc).replace(tzinfo=None),
                event_type=event_type,
                traccar_device_id=device_id,
                payload=payload,
            )
        )

        if event_type == "maintenance" and device_id is not None:
            vehicle, updated_ids = _mark_reminders_overdue(db, device_id, maintenance_id)
            if vehicle is not None and updated_ids:
                await notify_reminders_for_vehicle(
                    db, vehicle, reminder_ids=updated_ids, force=True
                )

        db.commit()
    except Exception:
        # Never bounce Traccar's forwarder with repeated 5xx.
        logger.exception("Failed to process Traccar webhook event")
        db.rollback()

    return {"status": "ok"}
