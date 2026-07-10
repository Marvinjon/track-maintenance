"""Reminder helpers: local CRUD, Traccar pull sync, and service-reset push.

Schedule definitions are pulled from Traccar (see maintenance_sync.py). The only
push to Traccar is updating maintenance ``start`` after a service is logged for
a Traccar-linked reminder.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Reminder, ServiceType, Vehicle
from app.services.odometer_sync import compute_reminder_status
from app.services.tenant_scope import catalog_visibility_filter, vehicle_catalog_tenant
from app.services.traccar import (
    TraccarService,
    TraccarPermissionDenied,
    UserCredential,
    hours_to_ms,
    km_to_meters,
)

logger = logging.getLogger(__name__)


def _maintenance_payload_km(
    reminder: Reminder, maintenance_name: str | None, maintenance_type: str
) -> dict:
    start_km = reminder.last_service_odometer_km or Decimal("0")
    payload: dict = {
        "type": maintenance_type,
        "start": km_to_meters(float(start_km)),
        "period": km_to_meters(float(reminder.interval_km)),
    }
    if maintenance_name:
        payload["name"] = maintenance_name
    return payload


def _maintenance_payload_hours(
    reminder: Reminder, maintenance_name: str | None, maintenance_type: str
) -> dict:
    start_h = reminder.last_service_engine_hours or Decimal("0")
    payload: dict = {
        "type": maintenance_type,
        "start": hours_to_ms(float(start_h)),
        "period": hours_to_ms(float(reminder.interval_hours)),
    }
    if maintenance_name:
        payload["name"] = maintenance_name
    return payload


async def push_traccar_maintenance_start(
    traccar: TraccarService,
    reminder: Reminder,
    credential: UserCredential | None = None,
) -> None:
    """Push updated start baseline to an existing Traccar maintenance entity."""
    if reminder.traccar_maintenance_id is None or credential is None:
        return

    maintenance_name = reminder.traccar_maintenance_name
    if reminder.interval_km is not None:
        maintenance_type = reminder.traccar_maintenance_type or "totalDistance"
        payload = _maintenance_payload_km(reminder, maintenance_name, maintenance_type)
    elif reminder.interval_hours is not None:
        maintenance_type = reminder.traccar_maintenance_type or "hours"
        payload = _maintenance_payload_hours(reminder, maintenance_name, maintenance_type)
    else:
        return

    try:
        await traccar.as_user(credential).update_maintenance(
            reminder.traccar_maintenance_id,
            {"id": reminder.traccar_maintenance_id, **payload},
        )
        reminder.sync_error = False
    except TraccarPermissionDenied:
        raise
    except Exception:
        logger.exception(
            "Failed to reset Traccar maintenance %s for reminder %s",
            reminder.traccar_maintenance_id,
            reminder.id,
        )
        reminder.sync_error = True


async def reset_reminders_after_service(
    db: Session,
    traccar: TraccarService,
    vehicle: Vehicle,
    service_type_id: int,
    performed_at,
    odometer_km: Decimal | None,
    credential: UserCredential,
) -> None:
    """After a service record is logged: update last_service_* and reset Traccar start."""
    reminders = (
        db.execute(
            select(Reminder).where(
                Reminder.vehicle_id == vehicle.id,
                Reminder.service_type_id == service_type_id,
            )
        )
        .scalars()
        .all()
    )
    for reminder in reminders:
        reminder.last_service_date = performed_at
        effective_odometer = (
            odometer_km if odometer_km is not None else vehicle.odometer_km_cached
        )
        if effective_odometer is not None:
            reminder.last_service_odometer_km = effective_odometer
        if vehicle.engine_hours_cached is not None:
            reminder.last_service_engine_hours = vehicle.engine_hours_cached
        reminder.status = compute_reminder_status(reminder, vehicle)
        if reminder.traccar_maintenance_id is not None:
            try:
                await push_traccar_maintenance_start(traccar, reminder, credential)
            except TraccarPermissionDenied:
                reminder.sync_error = True
                raise


async def create_default_reminders(
    db: Session,
    vehicle: Vehicle,
) -> list[Reminder]:
    """Create local-only reminders from service type default intervals."""
    tenant_id = vehicle_catalog_tenant(vehicle.traccar_tenant_user_id)
    service_types = db.execute(
        select(ServiceType).where(
            catalog_visibility_filter(ServiceType.traccar_tenant_user_id, tenant_id)
        )
    ).scalars().all()
    created: list[Reminder] = []
    for st in service_types:
        if st.default_interval_km is None and st.default_interval_days is None:
            continue
        reminder = Reminder(
            vehicle_id=vehicle.id,
            service_type_id=st.id,
            interval_km=st.default_interval_km,
            interval_days=st.default_interval_days,
            last_service_odometer_km=vehicle.odometer_km_cached,
            last_service_date=None,
            last_service_engine_hours=vehicle.engine_hours_cached,
        )
        reminder.status = compute_reminder_status(reminder, vehicle)
        db.add(reminder)
        db.flush()
        created.append(reminder)
    return created
