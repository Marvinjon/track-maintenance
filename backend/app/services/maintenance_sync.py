"""Pull Traccar maintenance schedules into local reminders.

Traccar is the source of truth for schedule definitions. Local-only reminders
(traccar_maintenance_id IS NULL) are never modified by this sync.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Reminder, ServiceType, Vehicle
from app.services.odometer_sync import compute_reminder_status
from app.services.reminders import push_traccar_maintenance_start
from app.services.traccar import (
    TraccarService,
    TraccarPermissionDenied,
    TraccarUnavailable,
    UserCredential,
    meters_to_km,
    ms_to_hours,
)
from app.services.tenant_scope import vehicle_catalog_tenant
from app.services.traccar_maintenance_types import (
    DISTANCE_MAINTENANCE_TYPES,
    HOURS_MAINTENANCE_TYPES,
    is_supported_maintenance_type,
)

logger = logging.getLogger(__name__)


@dataclass
class MaintenanceSyncResult:
    synced: int = 0
    created: int = 0
    updated: int = 0
    removed: int = 0
    skipped: int = 0


def _reminder_snapshot(reminder: Reminder) -> tuple:
    return (
        reminder.service_type_id,
        reminder.interval_km,
        reminder.interval_hours,
        reminder.interval_days,
        reminder.last_service_odometer_km,
        reminder.last_service_engine_hours,
        reminder.last_service_date,
        reminder.status,
        reminder.traccar_maintenance_type,
        reminder.traccar_maintenance_name,
    )


def _find_or_create_service_type(
    db: Session,
    name: str,
    *,
    interval_km: int | None,
    interval_hours: int | None,
    tenant_user_id: int | None,
) -> ServiceType:
    normalized = name.strip()
    filters = [func.lower(ServiceType.name) == normalized.lower()]
    if tenant_user_id is None:
        filters.append(ServiceType.traccar_tenant_user_id.is_(None))
    else:
        filters.append(ServiceType.traccar_tenant_user_id == tenant_user_id)
    existing = db.execute(select(ServiceType).where(*filters)).scalar_one_or_none()
    if existing is not None:
        return existing

    service_type = ServiceType(
        name=normalized,
        default_interval_km=interval_km,
        default_interval_days=None,
        traccar_tenant_user_id=tenant_user_id,
    )
    db.add(service_type)
    db.flush()
    return service_type


def _apply_traccar_maintenance(
    reminder: Reminder,
    maintenance: dict,
    vehicle: Vehicle,
) -> bool:
    """Apply Traccar fields. Returns False if maintenance type is unsupported."""
    maintenance_type = maintenance.get("type")
    start = maintenance.get("start")
    period = maintenance.get("period")

    if not is_supported_maintenance_type(maintenance_type):
        logger.warning(
            "Skipping Traccar maintenance %s with unsupported type %r",
            maintenance.get("id"),
            maintenance_type,
        )
        return False

    preserve_local_baseline = reminder.sync_error
    reminder.interval_days = None
    if not preserve_local_baseline:
        reminder.sync_error = False
    reminder.traccar_maintenance_type = maintenance_type
    reminder.traccar_maintenance_name = (maintenance.get("name") or "").strip() or None

    if maintenance_type in DISTANCE_MAINTENANCE_TYPES:
        reminder.interval_km = int(meters_to_km(float(period))) if period is not None else None
        reminder.interval_hours = None
        if not preserve_local_baseline:
            reminder.last_service_odometer_km = (
                Decimal(str(meters_to_km(float(start)))) if start is not None else None
            )
            reminder.last_service_engine_hours = None
    else:
        reminder.interval_hours = int(ms_to_hours(float(period))) if period is not None else None
        reminder.interval_km = None
        if not preserve_local_baseline:
            reminder.last_service_engine_hours = (
                Decimal(str(ms_to_hours(float(start)))) if start is not None else None
            )
            reminder.last_service_odometer_km = None

    reminder.status = compute_reminder_status(reminder, vehicle)
    return True


async def sync_vehicle_maintenances(
    db: Session,
    vehicle: Vehicle,
    traccar: TraccarService,
    credential: UserCredential,
    *,
    prune_missing: bool = True,
) -> MaintenanceSyncResult:
    """Pull Traccar maintenance entities for one vehicle into local reminders."""
    result = MaintenanceSyncResult()
    if vehicle.archived:
        return result

    try:
        maintenances = await traccar.as_user(credential).list_maintenances(
            vehicle.traccar_device_id
        )
    except TraccarPermissionDenied:
        logger.info(
            "Skipping maintenance sync for vehicle %s: caller cannot list Traccar schedules",
            vehicle.id,
        )
        return result
    except TraccarUnavailable:
        logger.warning(
            "Skipping maintenance sync for vehicle %s: Traccar maintenance list failed",
            vehicle.id,
        )
        return result

    seen_ids: set[int] = set()

    existing_by_traccar_id: dict[int, Reminder] = {
        r.traccar_maintenance_id: r
        for r in db.execute(
            select(Reminder).where(
                Reminder.vehicle_id == vehicle.id,
                Reminder.traccar_maintenance_id.is_not(None),
            )
        ).scalars()
        if r.traccar_maintenance_id is not None
    }

    for reminder in existing_by_traccar_id.values():
        if reminder.sync_error:
            await push_traccar_maintenance_start(traccar, reminder, credential)

    for maintenance in maintenances:
        traccar_id = maintenance.get("id")
        if traccar_id is None:
            continue
        traccar_id = int(traccar_id)

        maintenance_type = maintenance.get("type")
        if not is_supported_maintenance_type(maintenance_type):
            result.skipped += 1
            continue

        name = (maintenance.get("name") or "Maintenance").strip()
        period = maintenance.get("period")
        interval_km = None
        interval_hours = None
        if maintenance_type in DISTANCE_MAINTENANCE_TYPES and period is not None:
            interval_km = int(meters_to_km(float(period)))
        elif maintenance_type in HOURS_MAINTENANCE_TYPES and period is not None:
            interval_hours = int(ms_to_hours(float(period)))

        service_type = _find_or_create_service_type(
            db,
            name,
            interval_km=interval_km,
            interval_hours=interval_hours,
            tenant_user_id=vehicle_catalog_tenant(vehicle.traccar_tenant_user_id),
        )

        reminder = existing_by_traccar_id.get(traccar_id)
        is_new = reminder is None
        if is_new:
            reminder = Reminder(
                vehicle_id=vehicle.id,
                service_type_id=service_type.id,
                traccar_maintenance_id=traccar_id,
            )
            db.add(reminder)
            db.flush()
            existing_by_traccar_id[traccar_id] = reminder

        before = _reminder_snapshot(reminder)
        if not _apply_traccar_maintenance(reminder, maintenance, vehicle):
            result.skipped += 1
            if is_new:
                db.delete(reminder)
                del existing_by_traccar_id[traccar_id]
            continue

        if reminder.service_type_id != service_type.id:
            reminder.service_type_id = service_type.id

        seen_ids.add(traccar_id)
        result.synced += 1
        if is_new:
            result.created += 1
        elif _reminder_snapshot(reminder) != before:
            result.updated += 1

    if prune_missing:
        for traccar_id, reminder in list(existing_by_traccar_id.items()):
            if traccar_id not in seen_ids:
                db.delete(reminder)
                result.removed += 1
    elif existing_by_traccar_id:
        missing = [tid for tid in existing_by_traccar_id if tid not in seen_ids]
        if missing:
            logger.info(
                "Skipping maintenance prune for vehicle %s: caller has limited Traccar access (%d schedules not returned)",
                vehicle.id,
                len(missing),
            )

    return result
