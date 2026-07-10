"""Sync Traccar data for vehicles visible to the authenticated user.

Runs in the background after login and on session restore (/auth/me) so odometer
and maintenance schedules stay fresh without a server-wide admin token.
"""

from __future__ import annotations

import logging
import time
from typing import Hashable

from fastapi import BackgroundTasks

from app.services.maintenance_sync import sync_vehicle_maintenances
from app.services.odometer_sync import sync_vehicle
from app.services.traccar import UserCredential, get_traccar
from app.services.vehicles import active_vehicles_by_device

logger = logging.getLogger(__name__)

USER_SYNC_TTL_SECONDS = 300.0


class _SyncThrottle:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._last_sync: dict[Hashable, float] = {}

    def should_run(self, key: Hashable) -> bool:
        now = time.monotonic()
        last = self._last_sync.get(key)
        if last is not None and now - last < self._ttl:
            return False
        self._last_sync[key] = now
        return True

    def clear(self) -> None:
        self._last_sync.clear()


_sync_throttle = _SyncThrottle(USER_SYNC_TTL_SECONDS)


def clear_user_sync_throttle() -> None:
    """Used by tests."""
    _sync_throttle.clear()


async def sync_user_vehicles(
    credential: UserCredential,
    *,
    traccar_user_id: int | None = None,
    prune_missing_maintenance: bool = True,
) -> tuple[int, int]:
    """Pull odometer and maintenance for all registered vehicles the user can see."""
    from app.db import SessionLocal

    traccar = get_traccar()
    db = SessionLocal()
    odometer_synced = 0
    maintenance_synced = 0
    try:
        devices = await traccar.as_user(credential).list_devices()
        device_ids = [d["id"] for d in devices if isinstance(d.get("id"), int)]
        vehicles = active_vehicles_by_device(db, device_ids)

        for vehicle in vehicles.values():
            try:
                if await sync_vehicle(db, vehicle, traccar, credential):
                    odometer_synced += 1
                result = await sync_vehicle_maintenances(
                    db,
                    vehicle,
                    traccar,
                    credential,
                    prune_missing=prune_missing_maintenance,
                )
                if result.synced:
                    maintenance_synced += result.synced
            except Exception:
                logger.exception(
                    "User sync failed for vehicle %s (device %s)",
                    vehicle.id,
                    vehicle.traccar_device_id,
                )

        db.commit()
    except Exception:
        logger.exception("User sync failed for Traccar user %s", traccar_user_id)
        db.rollback()
    finally:
        db.close()

    if odometer_synced or maintenance_synced:
        logger.info(
            "User sync for Traccar user %s: %d odometer, %d maintenance",
            traccar_user_id,
            odometer_synced,
            maintenance_synced,
        )
    return odometer_synced, maintenance_synced


async def _run_user_sync(
    credential: UserCredential,
    traccar_user_id: int,
    prune_missing_maintenance: bool,
) -> None:
    await sync_user_vehicles(
        credential,
        traccar_user_id=traccar_user_id,
        prune_missing_maintenance=prune_missing_maintenance,
    )


def schedule_user_sync(
    background_tasks: BackgroundTasks,
    *,
    traccar_user_id: int,
    credential: UserCredential,
    force: bool = False,
    prune_missing_maintenance: bool = True,
) -> None:
    """Queue a background sync when due (or always when ``force``)."""
    if not force and not _sync_throttle.should_run(traccar_user_id):
        return
    background_tasks.add_task(
        _run_user_sync,
        credential,
        traccar_user_id,
        prune_missing_maintenance,
    )
