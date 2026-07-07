"""Odometer/engine-hours sync from Traccar + reminder status recomputation.

Used by the on-demand endpoint (POST /vehicles/{id}/sync-odometer) and by the
in-process APScheduler job that runs every 30 minutes. Both paths use the
admin token — the position fetch is a background concern, authorization for
the endpoint is checked separately with the user's own credentials.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Reminder, ReminderStatus, Vehicle
from app.services.traccar import (
    TraccarService,
    get_traccar,
    km_to_meters,
    meters_to_km,
    ms_to_hours,
)

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def apply_position_to_vehicle(vehicle: Vehicle, position: dict[str, Any]) -> None:
    """Update cached odometer/engine hours from a Traccar position.

    totalDistance and odometer attributes are meters; hours is milliseconds.
    """
    attributes = position.get("attributes", {})

    distance_m = attributes.get("totalDistance")
    if distance_m is None:
        distance_m = attributes.get("odometer")
    if distance_m is not None:
        vehicle.odometer_km_cached = Decimal(str(meters_to_km(distance_m)))

    hours_ms = attributes.get("hours")
    if hours_ms is not None:
        vehicle.engine_hours_cached = Decimal(str(ms_to_hours(hours_ms)))

    vehicle.odometer_synced_at = _utcnow_naive()


def apply_odometer_to_vehicle(vehicle: Vehicle, odometer_km: Decimal) -> None:
    """Update cached odometer from a user-entered reading (e.g. service log)."""
    vehicle.odometer_km_cached = odometer_km
    vehicle.odometer_synced_at = _utcnow_naive()


async def push_odometer_to_traccar(
    traccar: TraccarService, vehicle: Vehicle, odometer_km: Decimal
) -> None:
    """Push odometer to Traccar device accumulators via admin token.

    Best-effort: failures are logged but do not block the caller.
    """
    try:
        await traccar.as_admin().update_device_accumulators(
            vehicle.traccar_device_id,
            total_distance_m=km_to_meters(float(odometer_km)),
        )
    except Exception:
        logger.exception(
            "Failed to push odometer to Traccar for device %s",
            vehicle.traccar_device_id,
        )


async def apply_logged_odometer(
    db: Session,
    traccar: TraccarService,
    vehicle: Vehicle,
    odometer_km: Decimal,
) -> None:
    """Apply a logged odometer reading locally and mirror it to Traccar."""
    apply_odometer_to_vehicle(vehicle, odometer_km)
    await push_odometer_to_traccar(traccar, vehicle, odometer_km)
    recompute_vehicle_reminders(db, vehicle)


def compute_reminder_status(reminder: Reminder, vehicle: Vehicle) -> ReminderStatus:
    """due_soon within DUE_SOON_KM / DUE_SOON_DAYS of the threshold, overdue past it."""
    settings = get_settings()
    worst = ReminderStatus.ok

    def bump(candidate: ReminderStatus) -> None:
        nonlocal worst
        order = [ReminderStatus.ok, ReminderStatus.due_soon, ReminderStatus.overdue]
        if order.index(candidate) > order.index(worst):
            worst = candidate

    if (
        reminder.interval_km is not None
        and reminder.last_service_odometer_km is not None
        and vehicle.odometer_km_cached is not None
    ):
        next_due_km = reminder.last_service_odometer_km + reminder.interval_km
        current_km = vehicle.odometer_km_cached
        if current_km >= next_due_km:
            bump(ReminderStatus.overdue)
        elif current_km >= next_due_km - settings.due_soon_km:
            bump(ReminderStatus.due_soon)

    if reminder.interval_days is not None and reminder.last_service_date is not None:
        next_due_date = reminder.last_service_date + timedelta(days=reminder.interval_days)
        today = date.today()
        if today >= next_due_date:
            bump(ReminderStatus.overdue)
        elif today >= next_due_date - timedelta(days=settings.due_soon_days):
            bump(ReminderStatus.due_soon)

    if (
        reminder.interval_hours is not None
        and reminder.last_service_engine_hours is not None
        and vehicle.engine_hours_cached is not None
    ):
        next_due_hours = reminder.last_service_engine_hours + reminder.interval_hours
        current_hours = vehicle.engine_hours_cached
        if current_hours >= next_due_hours:
            bump(ReminderStatus.overdue)
        elif current_hours >= next_due_hours - settings.due_soon_hours:
            bump(ReminderStatus.due_soon)

    return worst


def recompute_vehicle_reminders(db: Session, vehicle: Vehicle) -> None:
    reminders = (
        db.execute(select(Reminder).where(Reminder.vehicle_id == vehicle.id))
        .scalars()
        .all()
    )
    for reminder in reminders:
        reminder.status = compute_reminder_status(reminder, vehicle)


async def sync_vehicle(db: Session, vehicle: Vehicle, traccar: TraccarService) -> bool:
    """Sync one vehicle. Returns True if a position was found and applied."""
    position = await traccar.as_admin().get_latest_position(vehicle.traccar_device_id)
    if position is None:
        return False
    apply_position_to_vehicle(vehicle, position)
    recompute_vehicle_reminders(db, vehicle)
    return True


async def sync_all_vehicles(db: Session, traccar: TraccarService) -> int:
    """Sync every non-archived vehicle. Returns the number synced."""
    vehicles = (
        db.execute(select(Vehicle).where(Vehicle.archived.is_(False))).scalars().all()
    )
    synced = 0
    for vehicle in vehicles:
        try:
            if await sync_vehicle(db, vehicle, traccar):
                synced += 1
        except Exception:
            logger.exception(
                "Odometer sync failed for vehicle %s (device %s)",
                vehicle.id,
                vehicle.traccar_device_id,
            )
    db.commit()
    return synced


async def run_scheduled_sync() -> None:
    """Entry point for the APScheduler job (owns its DB session)."""
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        synced = await sync_all_vehicles(db, get_traccar())
        logger.info("Scheduled odometer sync completed: %d vehicles updated", synced)
    except Exception:
        logger.exception("Scheduled odometer sync failed")
    finally:
        db.close()
