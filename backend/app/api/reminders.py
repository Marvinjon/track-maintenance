from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthorizedVehicle, CurrentUser, verify_device_access
from app.db import get_db
from app.models import Reminder, ServiceType, Vehicle
from app.services.vehicles import visible_vehicles
from app.schemas.reminders import (
    ReminderCreate,
    ReminderOut,
    ReminderUpdate,
    ReminderWithVehicleOut,
)
from app.services.odometer_sync import compute_reminder_status
from app.services.serialization import reminder_to_out
from app.services.traccar import TraccarService, get_traccar

router = APIRouter(tags=["reminders"])


def _require_service_type(db: Session, service_type_id: int) -> ServiceType:
    service_type = db.get(ServiceType, service_type_id)
    if service_type is None:
        raise HTTPException(status_code=422, detail="Unknown service type")
    return service_type


def _to_out(reminder: Reminder, service_type: ServiceType) -> ReminderOut:
    return reminder_to_out(reminder, service_type)


def _reject_traccar_linked(reminder: Reminder, action: str) -> None:
    if reminder.traccar_maintenance_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot {action} a reminder synced from Traccar; edit it in Traccar",
        )


async def _get_authorized_reminder(
    reminder_id: int,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> Reminder:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found"
        )
    vehicle = db.get(Vehicle, reminder.vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found"
        )
    await verify_device_access(ctx, traccar, vehicle.traccar_device_id)
    return reminder


AuthorizedReminder = Annotated[Reminder, Depends(_get_authorized_reminder)]

_STATUS_ORDER = {"overdue": 0, "due_soon": 1, "ok": 2}


@router.get("/reminders", response_model=list[ReminderWithVehicleOut])
async def list_all_reminders(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> list[ReminderWithVehicleOut]:
    """All reminders for vehicles the current user may see."""
    devices = await traccar.as_user(ctx.credential).list_devices()
    device_ids = [d["id"] for d in devices]
    device_names = {d["id"]: d.get("name") for d in devices}
    if not device_ids:
        return []

    vehicles = visible_vehicles(db, device_ids, active_only=True)
    if not vehicles:
        return []

    vehicle_ids = [v.id for v in vehicles]
    vehicles_by_id = {v.id: v for v in vehicles}

    rows = db.execute(
        select(Reminder, ServiceType)
        .join(ServiceType, Reminder.service_type_id == ServiceType.id)
        .where(Reminder.vehicle_id.in_(vehicle_ids))
    ).all()

    result: list[ReminderWithVehicleOut] = []
    for reminder, service_type in rows:
        vehicle = vehicles_by_id[reminder.vehicle_id]
        result.append(
            ReminderWithVehicleOut(
                **_to_out(reminder, service_type).model_dump(),
                vehicle_plate=vehicle.plate,
                vehicle_device_name=device_names.get(vehicle.traccar_device_id),
            )
        )

    result.sort(
        key=lambda r: (
            _STATUS_ORDER.get(r.status, 99),
            r.vehicle_plate or r.vehicle_device_name or "",
            r.service_type_name or "",
        )
    )
    return result


@router.get("/vehicles/{vehicle_id}/reminders", response_model=list[ReminderOut])
async def list_reminders(
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
) -> list[ReminderOut]:
    rows = db.execute(
        select(Reminder, ServiceType)
        .join(ServiceType, Reminder.service_type_id == ServiceType.id)
        .where(Reminder.vehicle_id == vehicle.id)
        .order_by(Reminder.id)
    ).all()
    return [_to_out(reminder, service_type) for reminder, service_type in rows]


@router.post(
    "/vehicles/{vehicle_id}/reminders",
    response_model=ReminderOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_reminder(
    body: ReminderCreate,
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
) -> ReminderOut:
    """Create a local-only reminder (not pushed to Traccar)."""
    service_type = _require_service_type(db, body.service_type_id)

    reminder = Reminder(vehicle_id=vehicle.id, **body.model_dump())
    reminder.status = compute_reminder_status(reminder, vehicle)
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return _to_out(reminder, service_type)


@router.patch("/reminders/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    body: ReminderUpdate,
    reminder: AuthorizedReminder,
    db: Annotated[Session, Depends(get_db)],
) -> ReminderOut:
    _reject_traccar_linked(reminder, "edit")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    if (
        reminder.interval_km is None
        and reminder.interval_days is None
        and reminder.interval_hours is None
    ):
        raise HTTPException(
            status_code=422, detail="Provide interval_km, interval_days, and/or interval_hours"
        )

    vehicle = db.get(Vehicle, reminder.vehicle_id)
    service_type = db.get(ServiceType, reminder.service_type_id)
    if service_type is None:
        raise HTTPException(status_code=422, detail="Unknown service type")
    reminder.status = compute_reminder_status(reminder, vehicle)

    db.commit()
    db.refresh(reminder)
    return _to_out(reminder, service_type)


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder: AuthorizedReminder,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a local-only reminder."""
    _reject_traccar_linked(reminder, "delete")
    db.delete(reminder)
    db.commit()
