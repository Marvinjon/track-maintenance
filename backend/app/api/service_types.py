from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.records import parts_by_record, _to_out as record_to_out
from app.db import get_db
from app.models import MaintenanceRecord, ServiceType, Vehicle
from app.schemas.records import FleetRecordListResponse, RecordWithVehicleOut
from app.schemas.service_types import ServiceTypeCreate, ServiceTypeOut, ServiceTypeUpdate
from app.schemas.importing import ImportResult, ImportRowError, ServiceTypeImportRequest
from app.services.serialization import service_type_to_out
from app.services.tenant_scope import (
    assert_catalog_visible,
    catalog_visibility_filter,
    create_tenant_id,
    tenant_name_conflict_filter,
)
from app.services.traccar import TraccarService, get_traccar

router = APIRouter(prefix="/service-types", tags=["service-types"])


def _get_service_type(db: Session, service_type_id: int, ctx: CurrentUser) -> ServiceType:
    service_type = db.get(ServiceType, service_type_id)
    if service_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service type not found"
        )
    assert_catalog_visible(
        service_type, ctx.tenant_user_id, detail="Service type not found"
    )
    return service_type


@router.get("", response_model=list[ServiceTypeOut])
async def list_service_types(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[ServiceTypeOut]:
    rows = db.execute(
        select(ServiceType)
        .where(
            catalog_visibility_filter(
                ServiceType.traccar_tenant_user_id, ctx.tenant_user_id
            )
        )
        .order_by(ServiceType.name)
    ).scalars()
    return [service_type_to_out(st) for st in rows]


@router.post("", response_model=ServiceTypeOut, status_code=status.HTTP_201_CREATED)
async def create_service_type(
    body: ServiceTypeCreate,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceTypeOut:
    tenant_id = create_tenant_id(ctx)
    name = body.name.strip()
    existing = db.execute(
        select(ServiceType).where(
            ServiceType.name == name,
            tenant_name_conflict_filter(ServiceType.traccar_tenant_user_id, tenant_id),
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A service type with this name already exists",
        )

    service_type = ServiceType(
        default_interval_km=body.default_interval_km,
        default_interval_days=body.default_interval_days,
        name=name,
        traccar_tenant_user_id=tenant_id,
    )
    db.add(service_type)
    db.commit()
    db.refresh(service_type)
    return service_type_to_out(service_type)


@router.post("/import", response_model=ImportResult)
async def import_service_types(
    body: ServiceTypeImportRequest,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ImportResult:
    """Bulk import service types from parsed CSV rows."""
    tenant_id = create_tenant_id(ctx)
    created = 0
    skipped = 0
    errors: list[ImportRowError] = []

    for index, row in enumerate(body.rows, start=1):
        name = row.name.strip()
        if not name:
            errors.append(ImportRowError(row=index, message="name is required"))
            continue

        existing = db.execute(
            select(ServiceType).where(
                ServiceType.name == name,
                tenant_name_conflict_filter(ServiceType.traccar_tenant_user_id, tenant_id),
            )
        ).scalar_one_or_none()
        if existing is not None:
            skipped += 1
            continue

        interval_km = None
        if row.default_interval_km.strip():
            try:
                interval_km = int(row.default_interval_km.strip())
                if interval_km <= 0:
                    raise ValueError()
            except ValueError:
                errors.append(
                    ImportRowError(row=index, message="default_interval_km must be a positive integer")
                )
                continue

        interval_days = None
        if row.default_interval_days.strip():
            try:
                interval_days = int(row.default_interval_days.strip())
                if interval_days <= 0:
                    raise ValueError()
            except ValueError:
                errors.append(
                    ImportRowError(row=index, message="default_interval_days must be a positive integer")
                )
                continue

        service_type = ServiceType(
            name=name,
            default_interval_km=interval_km,
            default_interval_days=interval_days,
            traccar_tenant_user_id=tenant_id,
        )
        db.add(service_type)
        created += 1

    if created > 0:
        db.commit()
    else:
        db.rollback()

    return ImportResult(created=created, skipped=skipped, errors=errors)


@router.patch("/{service_type_id}", response_model=ServiceTypeOut)
async def update_service_type(
    service_type_id: int,
    body: ServiceTypeUpdate,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ServiceTypeOut:
    service_type = _get_service_type(db, service_type_id, ctx)
    tenant_id = create_tenant_id(ctx)
    updates = body.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        updates["name"] = updates["name"].strip()
        existing = db.execute(
            select(ServiceType).where(
                ServiceType.name == updates["name"],
                ServiceType.id != service_type_id,
                tenant_name_conflict_filter(ServiceType.traccar_tenant_user_id, tenant_id),
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A service type with this name already exists",
            )
    for field, value in updates.items():
        setattr(service_type, field, value)
    db.commit()
    db.refresh(service_type)
    return service_type_to_out(service_type)


@router.get("/{service_type_id}/records", response_model=FleetRecordListResponse)
async def list_records_for_service_type(
    service_type_id: int,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FleetRecordListResponse:
    """Maintenance history for a service type across visible vehicles."""
    _get_service_type(db, service_type_id, ctx)

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
        .where(
            MaintenanceRecord.vehicle_id.in_(vehicle_ids),
            MaintenanceRecord.service_type_id == service_type_id,
        )
    ).scalar_one()

    rows = db.execute(
        select(MaintenanceRecord, ServiceType.name)
        .join(ServiceType, MaintenanceRecord.service_type_id == ServiceType.id)
        .where(
            MaintenanceRecord.vehicle_id.in_(vehicle_ids),
            MaintenanceRecord.service_type_id == service_type_id,
        )
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
                **record_to_out(record, name, parts_map.get(record.id, [])).model_dump(),
                vehicle_plate=vehicle.plate,
                vehicle_device_name=device_names.get(vehicle.traccar_device_id),
            )
        )

    return FleetRecordListResponse(
        items=items, total=total, limit=limit, offset=offset
    )
