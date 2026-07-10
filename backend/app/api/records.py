from decimal import Decimal

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    AuthorizedVehicle,
    CurrentUser,
    require_traccar_write_access,
    verify_device_access,
)
from app.db import get_db
from app.models import MaintenanceRecord, Part, RecordChange, RecordPart, ServiceType, Vehicle
from app.schemas.importing import ImportResult, RecordImportRequest
from app.schemas.records import (
    FleetRecordListResponse,
    RecordCreate,
    RecordDetailOut,
    RecordListResponse,
    RecordOut,
    RecordPartOut,
    RecordUpdate,
    RecordWithVehicleOut,
)
from app.services.record_import import create_record_with_side_effects, import_records
from app.services.record_audit import _snapshot, changes_for_record, log_record_changes
from app.services.odometer_sync import apply_logged_odometer
from app.services.stock import (
    apply_record_parts,
    detach_movements_from_record,
    reverse_record_parts,
)
from app.services.traccar import TraccarPermissionDenied, TraccarService, get_traccar
from app.services.tenant_scope import get_service_type

router = APIRouter(tags=["records"])


def parts_by_record(db: Session, record_ids: list[int]) -> dict[int, list[RecordPartOut]]:
    """record_id -> its parts (with names), for response assembly."""
    if not record_ids:
        return {}
    rows = db.execute(
        select(RecordPart, Part.name)
        .join(Part, RecordPart.part_id == Part.id)
        .where(RecordPart.maintenance_record_id.in_(record_ids))
        .order_by(RecordPart.id)
    ).all()
    result: dict[int, list[RecordPartOut]] = {}
    for record_part, part_name in rows:
        result.setdefault(record_part.maintenance_record_id, []).append(
            RecordPartOut(
                part_id=record_part.part_id,
                part_name=part_name,
                quantity=record_part.quantity,
            )
        )
    return result


def _to_out(
    record: MaintenanceRecord,
    service_type_name: str | None,
    parts: list[RecordPartOut],
) -> RecordOut:
    out = RecordOut.model_validate(record)
    return out.model_copy(
        update={"service_type_name": service_type_name, "parts": parts}
    )


async def _get_authorized_record(
    record_id: int,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> MaintenanceRecord:
    record = db.get(MaintenanceRecord, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    vehicle = db.get(Vehicle, record.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    await verify_device_access(ctx, traccar, vehicle.traccar_device_id)
    return record


AuthorizedRecord = Annotated[MaintenanceRecord, Depends(_get_authorized_record)]


@router.get("/records", response_model=FleetRecordListResponse)
async def list_all_records(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FleetRecordListResponse:
    """Maintenance history across all vehicles the current user may see."""
    devices = await traccar.as_user(ctx.credential).list_devices()
    device_ids = [d["id"] for d in devices]
    device_names = {d["id"]: d.get("name") for d in devices}
    if not device_ids:
        return FleetRecordListResponse(items=[], total=0, limit=limit, offset=offset)

    vehicles = db.execute(
        select(Vehicle).where(Vehicle.traccar_device_id.in_(device_ids))
    ).scalars().all()
    vehicle_ids = [v.id for v in vehicles]
    vehicles_by_id = {v.id: v for v in vehicles}
    if not vehicle_ids:
        return FleetRecordListResponse(items=[], total=0, limit=limit, offset=offset)

    total = db.execute(
        select(func.count())
        .select_from(MaintenanceRecord)
        .where(MaintenanceRecord.vehicle_id.in_(vehicle_ids))
    ).scalar_one()

    rows = db.execute(
        select(MaintenanceRecord, ServiceType.name)
        .join(ServiceType, MaintenanceRecord.service_type_id == ServiceType.id)
        .where(MaintenanceRecord.vehicle_id.in_(vehicle_ids))
        .order_by(MaintenanceRecord.performed_at.desc(), MaintenanceRecord.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    parts_map = parts_by_record(db, [record.id for record, _ in rows])
    items = []
    for record, name in rows:
        vehicle = vehicles_by_id[record.vehicle_id]
        items.append(
            RecordWithVehicleOut(
                **_to_out(record, name, parts_map.get(record.id, [])).model_dump(),
                vehicle_plate=vehicle.plate,
                vehicle_device_name=device_names.get(vehicle.traccar_device_id),
            )
        )

    return FleetRecordListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get("/vehicles/{vehicle_id}/records", response_model=RecordListResponse)
async def list_records(
    vehicle: AuthorizedVehicle,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RecordListResponse:
    """Maintenance history for a vehicle, newest first."""
    total = db.execute(
        select(func.count())
        .select_from(MaintenanceRecord)
        .where(MaintenanceRecord.vehicle_id == vehicle.id)
    ).scalar_one()

    rows = db.execute(
        select(MaintenanceRecord, ServiceType.name)
        .join(ServiceType, MaintenanceRecord.service_type_id == ServiceType.id)
        .where(MaintenanceRecord.vehicle_id == vehicle.id)
        .order_by(MaintenanceRecord.performed_at.desc(), MaintenanceRecord.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    parts_map = parts_by_record(db, [record.id for record, _ in rows])
    return RecordListResponse(
        items=[
            _to_out(record, name, parts_map.get(record.id, [])) for record, name in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/vehicles/{vehicle_id}/records",
    response_model=RecordOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_record(
    body: RecordCreate,
    vehicle: AuthorizedVehicle,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> RecordOut:
    """Create a record; any listed parts atomically create record_parts rows
    plus the matching negative stock movements (single transaction — a failure
    anywhere rolls back everything). A reminder linked to the same service
    type is reset and its Traccar mirror updated."""
    require_traccar_write_access(ctx)
    service_type = get_service_type(db, body.service_type_id, ctx.tenant_user_id)

    record, traccar_sync_warning = await create_record_with_side_effects(
        db,
        vehicle=vehicle,
        service_type=service_type,
        performed_at=body.performed_at,
        odometer_km=body.odometer_km,
        cost=body.cost,
        currency=body.currency,
        performed_by=body.performed_by,
        notes=body.notes,
        user_id=ctx.user.id,
        traccar=traccar,
        credential=ctx.credential,
    )

    apply_record_parts(
        db,
        record,
        [(p.part_id, p.quantity) for p in body.parts],
        ctx.user.id,
        ctx.tenant_user_id,
    )

    db.commit()
    db.refresh(record)
    parts_map = parts_by_record(db, [record.id])
    return _to_out(
        record,
        service_type.name,
        parts_map.get(record.id, []),
    ).model_copy(update={"traccar_sync_warning_code": traccar_sync_warning})


@router.post("/records/import", response_model=ImportResult)
async def import_records_endpoint(
    body: RecordImportRequest,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> ImportResult:
    """Bulk import maintenance records from parsed CSV rows."""
    require_traccar_write_access(ctx)
    return await import_records(
        db,
        rows=body.rows,
        user_id=ctx.user.id,
        tenant_user_id=ctx.tenant_user_id,
        traccar=traccar,
        credential=ctx.credential,
    )


@router.get("/records/{record_id}", response_model=RecordDetailOut)
async def get_record(
    record: AuthorizedRecord,
    db: Annotated[Session, Depends(get_db)],
) -> RecordDetailOut:
    service_type = db.get(ServiceType, record.service_type_id)
    parts_map = parts_by_record(db, [record.id])
    changes = changes_for_record(db, record.id)
    return RecordDetailOut(
        **_to_out(
            record,
            service_type.name if service_type else None,
            parts_map.get(record.id, []),
        ).model_dump(),
        changes=changes,
    )


@router.patch("/records/{record_id}", response_model=RecordOut)
async def update_record(
    body: RecordUpdate,
    record: AuthorizedRecord,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> RecordOut:
    require_traccar_write_access(ctx)
    updates = body.model_dump(exclude_unset=True)
    new_parts = updates.pop("parts", None)
    odometer_km = updates.pop("odometer_km", None)

    before = _snapshot(db, record)

    if "service_type_id" in updates:
        get_service_type(db, updates["service_type_id"], ctx.tenant_user_id)
    for field, value in updates.items():
        setattr(record, field, value)
    if odometer_km is not None:
        record.odometer_km = odometer_km

    vehicle = db.get(Vehicle, record.vehicle_id)
    traccar_sync_warning: str | None = None
    if odometer_km is not None and vehicle is not None:
        try:
            await apply_logged_odometer(
                db, traccar, vehicle, odometer_km, ctx.credential
            )
        except TraccarPermissionDenied:
            traccar_sync_warning = "no_traccar_permission"

    if new_parts is not None:
        # Replace parts: reverse the old movements, apply the new set.
        reverse_record_parts(db, record, ctx.user.id)
        apply_record_parts(
            db,
            record,
            [(p["part_id"], p["quantity"]) for p in new_parts],
            ctx.user.id,
            ctx.tenant_user_id,
        )

    after = _snapshot(db, record)
    log_record_changes(db, record, before, after, ctx.user.id)

    db.commit()
    db.refresh(record)
    service_type = db.get(ServiceType, record.service_type_id)
    parts_map = parts_by_record(db, [record.id])
    return _to_out(
        record,
        service_type.name if service_type else None,
        parts_map.get(record.id, []),
    ).model_copy(update={"traccar_sync_warning_code": traccar_sync_warning})


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record: AuthorizedRecord,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a record, reversing its stock movements with compensating
    ledger entries (the ledger itself is append-only and survives)."""
    require_traccar_write_access(ctx)
    reverse_record_parts(db, record, ctx.user.id)
    db.flush()
    detach_movements_from_record(db, record)
    db.execute(
        delete(RecordChange).where(RecordChange.maintenance_record_id == record.id)
    )
    db.delete(record)
    db.commit()
