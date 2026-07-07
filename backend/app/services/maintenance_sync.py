"""Pull Traccar maintenance schedules into local reminders (admin token).

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
from app.services.traccar import TraccarService, meters_to_km, ms_to_hours
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
    db: Session, name: str, *, interval_km: int | None, interval_hours: int | None
) -> ServiceType:
    normalized = name.strip()
    existing = db.execute(
        select(ServiceType).where(func.lower(ServiceType.name) == normalized.lower())
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    service_type = ServiceType(
        name=normalized,
        default_interval_km=interval_km,
        default_interval_days=None,
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
    db: Session, vehicle: Vehicle, traccar: TraccarService
) -> MaintenanceSyncResult:
    """Pull Traccar maintenance entities for one vehicle into local reminders."""
    result = MaintenanceSyncResult()
    if vehicle.archived:
        return result

    maintenances = await traccar.as_admin().list_maintenances(vehicle.traccar_device_id)
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
            await push_traccar_maintenance_start(traccar, reminder)

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
            db, name, interval_km=interval_km, interval_hours=interval_hours
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

    for traccar_id, reminder in list(existing_by_traccar_id.items()):
        if traccar_id not in seen_ids:
            db.delete(reminder)
            result.removed += 1

    return result


async def sync_all_vehicle_maintenances(
    db: Session, traccar: TraccarService
) -> MaintenanceSyncResult:
    """Pull Traccar maintenance for every non-archived vehicle."""
    totals = MaintenanceSyncResult()
    vehicles = (
        db.execute(select(Vehicle).where(Vehicle.archived.is_(False))).scalars().all()
    )
    for vehicle in vehicles:
        try:
            result = await sync_vehicle_maintenances(db, vehicle, traccar)
            totals.synced += result.synced
            totals.created += result.created
            totals.updated += result.updated
            totals.removed += result.removed
            totals.skipped += result.skipped
        except Exception:
            logger.exception(
                "Maintenance sync failed for vehicle %s (device %s)",
                vehicle.id,
                vehicle.traccar_device_id,
            )
    db.commit()
    return totals


async def run_scheduled_maintenance_sync() -> None:
    """Entry point for the APScheduler job (owns its DB session)."""
    from app.db import SessionLocal
    from app.services.traccar import get_traccar

    db = SessionLocal()
    try:
        totals = await sync_all_vehicle_maintenances(db, get_traccar())
        logger.info(
            "Scheduled maintenance sync completed: %d synced, %d created, "
            "%d updated, %d removed, %d skipped",
            totals.synced,
            totals.created,
            totals.updated,
            totals.removed,
            totals.skipped,
        )
    except Exception:
        logger.exception("Scheduled maintenance sync failed")
    finally:
        db.close()
