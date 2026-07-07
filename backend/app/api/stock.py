from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.parts import _to_out
from app.db import get_db
from app.models import Part
from app.schemas.parts import PartOut
from app.services.stock import current_stock_map

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/low", response_model=list[PartOut])
async def low_stock(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[PartOut]:
    """All non-archived parts whose current stock is below min_stock."""
    parts = (
        db.execute(select(Part).where(Part.archived.is_(False)).order_by(Part.name))
        .scalars()
        .all()
    )
    stock = current_stock_map(db, [p.id for p in parts])
    return [
        _to_out(p, stock.get(p.id, Decimal("0")))
        for p in parts
        if stock.get(p.id, Decimal("0")) < p.min_stock
    ]
