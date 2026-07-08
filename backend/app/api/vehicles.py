from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthorizedVehicle, CurrentUser, verify_device_access
from app.api.records import parts_by_record
from app.db import get_db
from app.models import MaintenanceRecord, Reminder, ReminderStatus, ServiceType, Vehicle
from app.schemas.records import RecordOut
from app.schemas.reminders import ReminderOut
from app.schemas.service_types import ServiceTypeOut
from app.schemas.vehicles import (
    VehicleBulkCreate,
    VehicleBulkCreateResult,
    VehicleCreate,
    VehicleDetail,
    VehicleOut,
    VehicleTransfer,
    VehicleTransferResult,
    VehicleUpdate,
)
from app.services.tenant_scope import create_tenant_id
from app.services.maintenance_sync import sync_vehicle_maintenances
from app.services.odometer_sync import sync_vehicle
from app.services.reminders import create_default_reminders
from app.services.serialization import reminder_to_out, service_type_to_out
from app.services.traccar import TraccarService, get_traccar
from app.services.vehicles import active_vehicle_for_device, active_vehicles_by_device

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

_STATUS_SEVERITY = {
    ReminderStatus.ok: 0,
    ReminderStatus.due_soon: 1,
    ReminderStatus.overdue: 2,
}


def _worst_status(statuses: list[ReminderStatus]) -> str | None:
    if not statuses:
        return None
    return max(statuses, key=lambda s: _STATUS_SEVERITY[s]).value


def _vehicle_fields(vehicle: Vehicle) -> dict:
    return {
        "id": vehicle.id,
        "plate": vehicle.plate,
        "vin": vehicle.vin,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "odometer_km_cached": vehicle.odometer_km_cached,
        "odometer_synced_at": vehicle.odometer_synced_at,
        "engine_hours_cached": vehicle.engine_hours_cached,
        "notes": vehicle.notes,
        "archived": vehicle.archived,
    }


@router.get("", response_model=list[VehicleOut])
async def list_vehicles(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> list[VehicleOut]:
    """All Traccar devices the current user may see, merged with local vehicle rows.

    Devices without a local row are returned as ``registered: false`` stubs so
    the UI can offer "Enable maintenance tracking".
    """
    devices = await traccar.as_user(ctx.credential).list_devices()
    device_ids = [d["id"] for d in devices]

    vehicles_by_device_id: dict[int, Vehicle] = {}
    last_service_by_vehicle: dict[int, object] = {}
    reminder_statuses_by_vehicle: dict[int, list[ReminderStatus]] = {}

    if device_ids:
        vehicles_by_device_id = active_vehicles_by_device(db, device_ids)

    vehicle_ids = [v.id for v in vehicles_by_device_id.values()]
    if vehicle_ids:
        for vehicle_id, last_date in db.execute(
            select(MaintenanceRecord.vehicle_id, func.max(MaintenanceRecord.performed_at))
            .where(MaintenanceRecord.vehicle_id.in_(vehicle_ids))
            .group_by(MaintenanceRecord.vehicle_id)
        ):
            last_service_by_vehicle[vehicle_id] = last_date
        for vehicle_id, reminder_status in db.execute(
            select(Reminder.vehicle_id, Reminder.status).where(
                Reminder.vehicle_id.in_(vehicle_ids)
            )
        ):
            reminder_statuses_by_vehicle.setdefault(vehicle_id, []).append(reminder_status)

    result: list[VehicleOut] = []
    for device in devices:
        vehicle = vehicles_by_device_id.get(device["id"])
        base = {
            "traccar_device_id": device["id"],
            "device_name": device.get("name"),
            "device_unique_id": device.get("uniqueId"),
            "device_status": device.get("status"),
        }
        if vehicle is None:
            result.append(VehicleOut(registered=False, **base))
        else:
            result.append(
                VehicleOut(
                    registered=True,
                    **base,
                    **_vehicle_fields(vehicle),
                    last_service_date=last_service_by_vehicle.get(vehicle.id),
                    reminder_status=_worst_status(
                        reminder_statuses_by_vehicle.get(vehicle.id, [])
                    ),
                )
            )
    return result


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: VehicleCreate,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> VehicleOut:
    """Enable maintenance tracking for a Traccar device the user can see."""
    await verify_device_access(ctx, traccar, body.traccar_device_id)

    existing = active_vehicle_for_device(db, body.traccar_device_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle already registered for this device",
        )

    vehicle = Vehicle(
        **body.model_dump(exclude={"create_default_reminders"}),
        traccar_tenant_user_id=create_tenant_id(ctx),
    )
    db.add(vehicle)
    db.flush()

    await sync_vehicle_maintenances(db, vehicle, traccar)

    if body.create_default_reminders:
        await create_default_reminders(db, vehicle)

    db.commit()
    db.refresh(vehicle)

    device = await traccar.as_user(ctx.credential).get_device(body.traccar_device_id)
    return VehicleOut(
        registered=True,
        traccar_device_id=vehicle.traccar_device_id,
        device_name=device.get("name") if device else None,
        device_unique_id=device.get("uniqueId") if device else None,
        device_status=device.get("status") if device else None,
        **_vehicle_fields(vehicle),
    )


@router.post("/bulk", response_model=VehicleBulkCreateResult, status_code=status.HTTP_201_CREATED)
async def bulk_create_vehicles(
    body: VehicleBulkCreate,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> VehicleBulkCreateResult:
    """Register multiple Traccar devices for maintenance tracking at once."""
    created: list[VehicleOut] = []
    skipped: list[int] = []

    for device_id in body.traccar_device_ids:
        try:
            await verify_device_access(ctx, traccar, device_id)
        except HTTPException:
            skipped.append(device_id)
            continue

        existing = active_vehicle_for_device(db, device_id)
        if existing is not None:
            skipped.append(device_id)
            continue

        vehicle = Vehicle(
            traccar_device_id=device_id,
            traccar_tenant_user_id=create_tenant_id(ctx),
        )
        db.add(vehicle)
        db.flush()

        await sync_vehicle_maintenances(db, vehicle, traccar)

        if body.create_default_reminders:
            await create_default_reminders(db, vehicle)

        device = await traccar.as_user(ctx.credential).get_device(device_id)
        created.append(
            VehicleOut(
                registered=True,
                traccar_device_id=vehicle.traccar_device_id,
                device_name=device.get("name") if device else None,
                device_unique_id=device.get("uniqueId") if device else None,
                device_status=device.get("status") if device else None,
                **_vehicle_fields(vehicle),
            )
        )

    db.commit()
    return VehicleBulkCreateResult(created=created, skipped=skipped)


@router.get("/{vehicle_id}", response_model=VehicleDetail)
async def get_vehicle(
    vehicle: AuthorizedVehicle,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> VehicleDetail:
    """Vehicle detail: cached odometer, reminders, last 5 records."""
    device = await traccar.as_user(ctx.credential).get_device(vehicle.traccar_device_id)

    reminder_rows = db.execute(
        select(Reminder, ServiceType)
        .join(ServiceType, Reminder.service_type_id == ServiceType.id)
        .where(Reminder.vehicle_id == vehicle.id)
        .order_by(Reminder.id)
    ).all()
    reminders = [reminder for reminder, _ in reminder_rows]
    recent = db.execute(
        select(MaintenanceRecord, ServiceType)
        .join(ServiceType, MaintenanceRecord.service_type_id == ServiceType.id)
        .where(MaintenanceRecord.vehicle_id == vehicle.id)
        .order_by(MaintenanceRecord.performed_at.desc(), MaintenanceRecord.id.desc())
        .limit(5)
    ).all()
    parts_map = parts_by_record(db, [record.id for record, _ in recent])

    last_service = db.execute(
        select(func.max(MaintenanceRecord.performed_at)).where(
            MaintenanceRecord.vehicle_id == vehicle.id
        )
    ).scalar_one_or_none()

    return VehicleDetail(
        registered=True,
        traccar_device_id=vehicle.traccar_device_id,
        device_name=device.get("name") if device else None,
        device_unique_id=device.get("uniqueId") if device else None,
        device_status=device.get("status") if device else None,
        **_vehicle_fields(vehicle),
        last_service_date=last_service,
        reminder_status=_worst_status([r.status for r in reminders]),
        reminders=[
            reminder_to_out(reminder, service_type)
            for reminder, service_type in reminder_rows
        ],
        recent_records=[
            RecordOut.model_validate(record).model_copy(
                update={
                    "service_type_name": service_type.name,
                    "parts": parts_map.get(record.id, []),
                }
            )
            for record, service_type in recent
        ],
    )


@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    body: VehicleUpdate,
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
) -> VehicleOut:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return VehicleOut(
        registered=True,
        traccar_device_id=vehicle.traccar_device_id,
        **_vehicle_fields(vehicle),
    )


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_vehicle(
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Soft archive — the row and its history are kept."""
    if vehicle.archived:
        return
    vehicle.archived = True
    db.commit()


@router.post("/{vehicle_id}/transfer", response_model=VehicleTransferResult)
async def transfer_tracker(
    body: VehicleTransfer,
    vehicle: AuthorizedVehicle,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> VehicleTransferResult:
    """Archive the current vehicle and open a fresh profile on the same tracker.

    Service history stays on the archived row. Reminders are not copied; optional
    default reminders can be created for the new row. The Traccar device name can
    be updated before or after this call.
    """
    if vehicle.archived:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vehicle is already archived",
        )

    archived_vehicle_id = vehicle.id
    vehicle.archived = True
    db.flush()

    new_vehicle = Vehicle(
        traccar_device_id=vehicle.traccar_device_id,
        plate=body.plate,
        vin=body.vin,
        make=body.make,
        model=body.model,
        year=body.year,
        notes=body.notes,
        traccar_tenant_user_id=vehicle.traccar_tenant_user_id or create_tenant_id(ctx),
    )
    db.add(new_vehicle)
    db.flush()

    if body.sync_odometer:
        await sync_vehicle(db, new_vehicle, traccar)

    await sync_vehicle_maintenances(db, new_vehicle, traccar)

    if body.create_default_reminders:
        await create_default_reminders(db, new_vehicle)

    db.commit()
    db.refresh(new_vehicle)

    device = await traccar.as_user(ctx.credential).get_device(new_vehicle.traccar_device_id)
    return VehicleTransferResult(
        archived_vehicle_id=archived_vehicle_id,
        vehicle=VehicleOut(
            registered=True,
            traccar_device_id=new_vehicle.traccar_device_id,
            device_name=device.get("name") if device else None,
            device_unique_id=device.get("uniqueId") if device else None,
            device_status=device.get("status") if device else None,
            **_vehicle_fields(new_vehicle),
        ),
    )


@router.get("/{vehicle_id}/log-service-types", response_model=list[ServiceTypeOut])
async def list_log_service_types(
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
) -> list[ServiceTypeOut]:
    """Service types available when logging maintenance for this vehicle.

    Includes types from this vehicle's reminders plus local-only types (not used
    by any Traccar-synced reminder).
    """
    reminder_type_ids = {
        row
        for row in db.execute(
            select(Reminder.service_type_id).where(Reminder.vehicle_id == vehicle.id)
        ).scalars()
    }
    traccar_synced_type_ids = {
        row
        for row in db.execute(
            select(Reminder.service_type_id).where(
                Reminder.traccar_maintenance_id.is_not(None)
            )
        ).scalars()
    }
    service_types: dict[int, ServiceType] = {}
    if reminder_type_ids:
        for service_type in db.execute(
            select(ServiceType).where(ServiceType.id.in_(reminder_type_ids))
        ).scalars():
            service_types[service_type.id] = service_type
    for service_type in db.execute(select(ServiceType)).scalars():
        if service_type.id not in traccar_synced_type_ids:
            service_types[service_type.id] = service_type
    return [
        service_type_to_out(st)
        for st in sorted(service_types.values(), key=lambda st: st.name.casefold())
    ]


@router.post("/{vehicle_id}/sync-maintenance")
async def sync_maintenance(
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> dict[str, int]:
    """On-demand pull of maintenance schedules from Traccar."""
    result = await sync_vehicle_maintenances(db, vehicle, traccar)
    db.commit()
    return {
        "synced": result.synced,
        "created": result.created,
        "updated": result.updated,
        "removed": result.removed,
        "skipped": result.skipped,
    }


@router.post("/{vehicle_id}/sync-odometer", response_model=VehicleOut)
async def sync_odometer(
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> VehicleOut:
    """On-demand pull of the latest position from Traccar.

    Reads attributes.totalDistance (m -> km, falling back to attributes.odometer)
    and attributes.hours (ms -> h).
    """
    found = await sync_vehicle(db, vehicle, traccar)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No position available for this device yet",
        )
    db.commit()
    db.refresh(vehicle)
    return VehicleOut(
        registered=True,
        traccar_device_id=vehicle.traccar_device_id,
        **_vehicle_fields(vehicle),
    )
