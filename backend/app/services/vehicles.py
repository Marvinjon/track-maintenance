"""Vehicle lookup helpers for device-scoped queries."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Vehicle


def active_vehicle_for_device(db: Session, traccar_device_id: int) -> Vehicle | None:
    return db.execute(
        select(Vehicle).where(
            Vehicle.traccar_device_id == traccar_device_id,
            Vehicle.archived.is_(False),
        )
    ).scalar_one_or_none()


def active_vehicles_by_device(
    db: Session, traccar_device_ids: list[int]
) -> dict[int, Vehicle]:
    if not traccar_device_ids:
        return {}
    rows = (
        db.execute(
            select(Vehicle).where(
                Vehicle.traccar_device_id.in_(traccar_device_ids),
                Vehicle.archived.is_(False),
            )
        )
        .scalars()
        .all()
    )
    return {v.traccar_device_id: v for v in rows}


def visible_vehicles(
    db: Session,
    traccar_device_ids: list[int],
    *,
    active_only: bool = False,
) -> list[Vehicle]:
    if not traccar_device_ids:
        return []
    query = select(Vehicle).where(Vehicle.traccar_device_id.in_(traccar_device_ids))
    if active_only:
        query = query.where(Vehicle.archived.is_(False))
    return list(db.execute(query).scalars().all())
