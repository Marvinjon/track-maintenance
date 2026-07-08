"""Bulk CSV import for maintenance records."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MaintenanceRecord, ServiceType, Vehicle
from app.schemas.importing import ImportResult, ImportRowError, RecordImportRow
from app.services.odometer_sync import apply_logged_odometer
from app.services.reminders import reset_reminders_after_service
from app.services.tenant_scope import list_visible_service_types
from app.services.traccar import TraccarService


def _norm(value: str) -> str:
    return value.strip()


def _norm_key(value: str) -> str:
    return _norm(value).casefold()


def _parse_optional_decimal(value: str, field: str) -> Decimal | None:
    text = _norm(value)
    if not text:
        return None
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {field}") from exc
    if result < 0:
        raise ValueError(f"{field} must be >= 0")
    return result


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%y",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%Y.%m.%d",
)


def _parse_date(value: str) -> date:
    text = _norm(value)
    if not text:
        raise ValueError("performed_at is required")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        "performed_at must be a valid date (e.g. YYYY-MM-DD, M/D/YY, or D.M.YYYY)"
    )


async def create_record_with_side_effects(
    db: Session,
    *,
    vehicle: Vehicle,
    service_type: ServiceType,
    performed_at: date,
    odometer_km: Decimal | None,
    cost: Decimal | None,
    currency: str,
    performed_by: str | None,
    notes: str | None,
    user_id: int,
    traccar: TraccarService,
) -> MaintenanceRecord:
    record = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        performed_at=performed_at,
        odometer_km=odometer_km,
        cost=cost,
        currency=currency,
        performed_by=performed_by,
        notes=notes,
        created_by_traccar_user_id=user_id,
    )
    db.add(record)
    db.flush()

    if record.odometer_km is not None:
        await apply_logged_odometer(db, traccar, vehicle, record.odometer_km)

    await reset_reminders_after_service(
        db,
        traccar,
        vehicle,
        service_type_id=service_type.id,
        performed_at=record.performed_at,
        odometer_km=record.odometer_km,
    )
    return record


async def import_records(
    db: Session,
    *,
    rows: list[RecordImportRow],
    user_id: int,
    tenant_user_id: int | None,
    traccar: TraccarService,
    credential: str,
) -> ImportResult:
    if len(rows) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Too many rows (max 500)",
        )

    devices = await traccar.as_user(credential).list_devices()
    device_ids = [d["id"] for d in devices]
    device_names = {d["id"]: d.get("name") for d in devices}

    vehicles_by_plate: dict[str, Vehicle] = {}
    vehicles_by_device: dict[str, Vehicle] = {}
    if device_ids:
        vehicles = db.execute(
            select(Vehicle).where(Vehicle.traccar_device_id.in_(device_ids))
        ).scalars().all()
        for vehicle in vehicles:
            if vehicle.plate:
                vehicles_by_plate[_norm_key(vehicle.plate)] = vehicle
            device_name = device_names.get(vehicle.traccar_device_id)
            if device_name:
                vehicles_by_device[_norm_key(device_name)] = vehicle

    service_types_by_name: dict[str, ServiceType] = {}
    for service_type in list_visible_service_types(db, tenant_user_id):
        service_types_by_name[_norm_key(service_type.name)] = service_type

    created = 0
    skipped = 0
    errors: list[ImportRowError] = []

    for index, row in enumerate(rows, start=1):
        try:
            plate = _norm(row.vehicle_plate)
            device = _norm(row.vehicle_device)
            if not plate and not device:
                raise ValueError("vehicle_plate or vehicle_device is required")

            vehicle = None
            if plate:
                vehicle = vehicles_by_plate.get(_norm_key(plate))
            if vehicle is None and device:
                vehicle = vehicles_by_device.get(_norm_key(device))
            if vehicle is None:
                raise ValueError("Unknown vehicle")

            service_type_name = _norm(row.service_type)
            if not service_type_name:
                raise ValueError("service_type is required")
            service_type = service_types_by_name.get(_norm_key(service_type_name))
            if service_type is None:
                raise ValueError(f"Unknown service type: {service_type_name}")

            performed_at = _parse_date(row.performed_at)
            odometer_km = _parse_optional_decimal(row.odometer_km, "odometer_km")
            cost = _parse_optional_decimal(row.cost, "cost")

            currency = _norm(row.currency) or "ISK"
            if len(currency) != 3:
                raise ValueError("currency must be a 3-letter code")

            performed_by = _norm(row.performed_by) or None
            if performed_by and len(performed_by) > 120:
                raise ValueError("performed_by is too long")
            notes = _norm(row.notes) or None

            await create_record_with_side_effects(
                db,
                vehicle=vehicle,
                service_type=service_type,
                performed_at=performed_at,
                odometer_km=odometer_km,
                cost=cost,
                currency=currency,
                performed_by=performed_by,
                notes=notes,
                user_id=user_id,
                traccar=traccar,
            )
            created += 1
        except ValueError as exc:
            errors.append(ImportRowError(row=index, message=str(exc)))

    if created > 0:
        db.commit()
    else:
        db.rollback()

    return ImportResult(created=created, skipped=skipped, errors=errors)
