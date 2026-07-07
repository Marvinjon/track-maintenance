from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MaintenanceRecord, RecordChange, ServiceType

TRACKED_FIELDS = (
    "service_type",
    "performed_at",
    "odometer_km",
    "cost",
    "currency",
    "performed_by",
    "notes",
)


def _service_type_name(db: Session, service_type_id: int) -> str:
    service_type = db.get(ServiceType, service_type_id)
    return service_type.name if service_type else str(service_type_id)


def _snapshot(db: Session, record: MaintenanceRecord) -> dict[str, object | None]:
    return {
        "service_type": _service_type_name(db, record.service_type_id),
        "performed_at": record.performed_at,
        "odometer_km": record.odometer_km,
        "cost": record.cost,
        "currency": record.currency,
        "performed_by": record.performed_by,
        "notes": record.notes,
    }


def _serialize(field: str, value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        normalized = value.normalize()
        text = format(normalized, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text
    text = str(value).strip()
    return text if text else None


def _equal(field: str, old: object | None, new: object | None) -> bool:
    if old is None and new is None:
        return True
    if field in {"cost", "odometer_km"}:
        if old is None or new is None:
            return old is new
        return Decimal(str(old)) == Decimal(str(new))
    if field == "performed_at":
        return old == new
    return (old or "") == (new or "")


def log_record_changes(
    db: Session,
    record: MaintenanceRecord,
    before: dict[str, object | None],
    after: dict[str, object | None],
    user_id: int,
) -> list[RecordChange]:
    changes: list[RecordChange] = []
    for field in TRACKED_FIELDS:
        old = before.get(field)
        new = after.get(field)
        if _equal(field, old, new):
            continue
        change = RecordChange(
            maintenance_record_id=record.id,
            field=field,
            old_value=_serialize(field, old),
            new_value=_serialize(field, new),
            changed_by_traccar_user_id=user_id,
        )
        db.add(change)
        changes.append(change)
    return changes


def changes_for_record(db: Session, record_id: int) -> list[RecordChange]:
    return list(
        db.execute(
            select(RecordChange)
            .where(RecordChange.maintenance_record_id == record_id)
            .order_by(RecordChange.created_at.desc(), RecordChange.id.desc())
        ).scalars()
    )
