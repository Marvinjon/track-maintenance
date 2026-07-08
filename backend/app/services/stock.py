"""Stock ledger helpers.

stock_movements is an append-only ledger: current stock for a part is always
SUM(quantity). Nothing here commits — callers own the transaction so that
record + record_parts + movements are atomic (a failed request rolls back
everything).
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    MaintenanceRecord,
    Part,
    RecordPart,
    StockMovement,
    StockMovementReason,
)


def current_stock_map(db: Session, part_ids: list[int] | None = None) -> dict[int, Decimal]:
    """part_id -> SUM(quantity), one GROUP BY query. Parts with no movements are absent."""
    query = select(StockMovement.part_id, func.sum(StockMovement.quantity)).group_by(
        StockMovement.part_id
    )
    if part_ids is not None:
        if not part_ids:
            return {}
        query = query.where(StockMovement.part_id.in_(part_ids))
    return {part_id: total for part_id, total in db.execute(query)}


def current_stock(db: Session, part_id: int) -> Decimal:
    return current_stock_map(db, [part_id]).get(part_id, Decimal("0"))


def add_movement(
    db: Session,
    *,
    part_id: int,
    quantity: Decimal,
    reason: StockMovementReason,
    user_id: int,
    maintenance_record_id: int | None = None,
    note: str | None = None,
) -> StockMovement:
    movement = StockMovement(
        part_id=part_id,
        quantity=quantity,
        reason=reason,
        maintenance_record_id=maintenance_record_id,
        note=note,
        created_by_traccar_user_id=user_id,
    )
    db.add(movement)
    return movement


from app.services.tenant_scope import get_part as get_visible_part


def _require_active_part(
    db: Session, part_id: int, tenant_user_id: int | None
) -> Part:
    part = db.get(Part, part_id)
    if part is None:
        raise HTTPException(status_code=422, detail=f"Unknown part id {part_id}")
    try:
        return get_visible_part(db, part_id, tenant_user_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=422, detail=f"Unknown part id {part_id}"
            ) from exc
        raise


def apply_record_parts(
    db: Session,
    record: MaintenanceRecord,
    parts: list[tuple[int, Decimal]],
    user_id: int,
    tenant_user_id: int | None,
) -> None:
    """Attach parts to a maintenance record: one record_parts row and the
    matching negative used_in_service movement per part, same transaction."""
    for part_id, quantity in parts:
        part = _require_active_part(db, part_id, tenant_user_id)
        db.add(
            RecordPart(
                maintenance_record_id=record.id,
                part_id=part.id,
                quantity=quantity,
            )
        )
        add_movement(
            db,
            part_id=part.id,
            quantity=-quantity,
            reason=StockMovementReason.used_in_service,
            user_id=user_id,
            maintenance_record_id=record.id,
            note=f"Used in service record #{record.id}",
        )


def reverse_record_parts(db: Session, record: MaintenanceRecord, user_id: int) -> None:
    """Remove a record's parts: delete record_parts rows and append reversing
    positive movements (the ledger itself is never mutated or deleted)."""
    record_parts = (
        db.execute(select(RecordPart).where(RecordPart.maintenance_record_id == record.id))
        .scalars()
        .all()
    )
    for record_part in record_parts:
        add_movement(
            db,
            part_id=record_part.part_id,
            quantity=record_part.quantity,
            reason=StockMovementReason.return_,
            user_id=user_id,
            maintenance_record_id=record.id,
            note=f"Reversal for service record #{record.id}",
        )
        db.delete(record_part)


def detach_movements_from_record(db: Session, record: MaintenanceRecord) -> None:
    """Before hard-deleting a record, null out the ledger's FK references so
    the append-only movements survive; the note still names the record."""
    movements = (
        db.execute(
            select(StockMovement).where(StockMovement.maintenance_record_id == record.id)
        )
        .scalars()
        .all()
    )
    for movement in movements:
        movement.maintenance_record_id = None
        if movement.note is None:
            movement.note = f"Service record #{record.id} (deleted)"
