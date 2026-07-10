from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_traccar_write_access
from app.db import get_db
from app.models import Part, StockMovement, StockMovementReason
from app.schemas.parts import (
    MovementCreate,
    MovementListResponse,
    MovementOut,
    PartCreate,
    PartOut,
    PartUpdate,
)
from app.schemas.importing import ImportResult, ImportRowError, PartImportRequest
from app.services.stock import add_movement, current_stock_map
from app.services.tenant_scope import (
    assert_catalog_deletable,
    assert_catalog_visible,
    catalog_visibility_filter,
    create_tenant_id,
    tenant_name_conflict_filter,
)

router = APIRouter(prefix="/parts", tags=["parts"])


def _to_out(part: Part, stock: Decimal) -> PartOut:
    out = PartOut.model_validate(part)
    return out.model_copy(
        update={"current_stock": stock, "low_stock": stock < part.min_stock}
    )


def _get_part(db: Session, part_id: int, ctx: CurrentUser) -> Part:
    part = db.get(Part, part_id)
    if part is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    assert_catalog_visible(part, ctx.tenant_user_id, detail="Part not found")
    return part


@router.get("", response_model=list[PartOut])
async def list_parts(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    include_archived: bool = False,
) -> list[PartOut]:
    query = (
        select(Part)
        .where(catalog_visibility_filter(Part.traccar_tenant_user_id, ctx.tenant_user_id))
        .order_by(Part.name)
    )
    if not include_archived:
        query = query.where(Part.archived.is_(False))
    parts = db.execute(query).scalars().all()
    stock = current_stock_map(db, [p.id for p in parts])
    return [_to_out(p, stock.get(p.id, Decimal("0"))) for p in parts]


@router.post("", response_model=PartOut, status_code=status.HTTP_201_CREATED)
async def create_part(
    body: PartCreate,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> PartOut:
    tenant_id = create_tenant_id(ctx)
    if body.sku is not None:
        existing = db.execute(
            select(Part).where(
                Part.sku == body.sku,
                tenant_name_conflict_filter(Part.traccar_tenant_user_id, tenant_id),
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="SKU already exists"
            )
    part = Part(**body.model_dump(), traccar_tenant_user_id=tenant_id)
    db.add(part)
    db.commit()
    db.refresh(part)
    return _to_out(part, Decimal("0"))


@router.post("/import", response_model=ImportResult)
async def import_parts(
    body: PartImportRequest,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ImportResult:
    """Bulk import parts from parsed CSV rows."""
    tenant_id = create_tenant_id(ctx)
    created = 0
    skipped = 0
    errors: list[ImportRowError] = []

    for index, row in enumerate(body.rows, start=1):
        name = row.name.strip()
        if not name:
            errors.append(ImportRowError(row=index, message="name is required"))
            continue

        sku = row.sku.strip() or None
        if sku:
            existing = db.execute(
                select(Part).where(
                    Part.sku == sku,
                    tenant_name_conflict_filter(Part.traccar_tenant_user_id, tenant_id),
                )
            ).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                continue

        unit = row.unit.strip() or "pcs"

        min_stock = Decimal("0")
        if row.min_stock.strip():
            try:
                min_stock = Decimal(row.min_stock.strip())
                if min_stock < 0:
                    raise ValueError()
            except (InvalidOperation, ValueError):
                errors.append(ImportRowError(row=index, message="min_stock must be >= 0"))
                continue

        unit_cost = None
        if row.unit_cost.strip():
            try:
                unit_cost = Decimal(row.unit_cost.strip())
                if unit_cost < 0:
                    raise ValueError()
            except (InvalidOperation, ValueError):
                errors.append(ImportRowError(row=index, message="unit_cost must be >= 0"))
                continue

        initial_stock = Decimal("0")
        if row.initial_stock.strip():
            try:
                initial_stock = Decimal(row.initial_stock.strip())
                if initial_stock < 0:
                    raise ValueError()
            except (InvalidOperation, ValueError):
                errors.append(ImportRowError(row=index, message="initial_stock must be >= 0"))
                continue

        part = Part(
            name=name,
            sku=sku,
            unit=unit,
            min_stock=min_stock,
            unit_cost=unit_cost,
            traccar_tenant_user_id=tenant_id,
        )
        db.add(part)
        db.flush()

        if initial_stock > 0:
            add_movement(
                db,
                part_id=part.id,
                quantity=initial_stock,
                reason=StockMovementReason.purchase,
                user_id=ctx.user.id,
                note="CSV import",
            )

        created += 1

    if created > 0:
        db.commit()
    else:
        db.rollback()

    return ImportResult(created=created, skipped=skipped, errors=errors)


@router.patch("/{part_id}", response_model=PartOut)
async def update_part(
    part_id: int,
    body: PartUpdate,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> PartOut:
    part = _get_part(db, part_id, ctx)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(part, field, value)
    db.commit()
    db.refresh(part)
    stock = current_stock_map(db, [part.id]).get(part.id, Decimal("0"))
    return _to_out(part, stock)


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_part(
    part_id: int,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Soft archive — the ledger history is kept."""
    require_traccar_write_access(ctx)
    part = _get_part(db, part_id, ctx)
    assert_catalog_deletable(part, ctx.tenant_user_id)
    part.archived = True
    db.commit()


@router.post(
    "/{part_id}/movements",
    response_model=MovementOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_movement(
    part_id: int,
    body: MovementCreate,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> MovementOut:
    """Manual ledger entry (purchase / adjustment / return)."""
    part = _get_part(db, part_id, ctx)
    if body.quantity == 0:
        raise HTTPException(status_code=422, detail="Quantity must not be zero")
    movement = add_movement(
        db,
        part_id=part.id,
        quantity=body.quantity,
        reason=StockMovementReason(body.reason),
        user_id=ctx.user.id,
        note=body.note,
    )
    db.commit()
    db.refresh(movement)
    return MovementOut.model_validate(movement)


@router.get("/{part_id}/movements", response_model=MovementListResponse)
async def list_movements(
    part_id: int,
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MovementListResponse:
    """Ledger view, newest first."""
    _get_part(db, part_id, ctx)
    total = db.execute(
        select(func.count())
        .select_from(StockMovement)
        .where(StockMovement.part_id == part_id)
    ).scalar_one()
    movements = (
        db.execute(
            select(StockMovement)
            .where(StockMovement.part_id == part_id)
            .order_by(StockMovement.id.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return MovementListResponse(
        items=[MovementOut.model_validate(m) for m in movements],
        total=total,
        limit=limit,
        offset=offset,
    )
