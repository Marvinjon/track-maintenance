from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PartCreate(BaseModel):
    sku: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=150)
    unit: str = Field(default="pcs", max_length=20)
    min_stock: Decimal = Field(default=Decimal("0"), ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)


class PartUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    unit: str | None = Field(default=None, max_length=20)
    min_stock: Decimal | None = Field(default=None, ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    archived: bool | None = None


class PartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str | None
    name: str
    unit: str
    min_stock: Decimal
    unit_cost: Decimal | None
    archived: bool
    created_at: datetime

    current_stock: Decimal = Decimal("0")
    low_stock: bool = False


# Manual ledger entries: used_in_service is reserved for record-parts,
# which are created through maintenance records only.
ManualMovementReason = Literal["purchase", "adjustment", "return"]


class MovementCreate(BaseModel):
    quantity: Decimal
    reason: ManualMovementReason
    note: str | None = Field(default=None, max_length=255)


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    quantity: Decimal
    reason: str
    maintenance_record_id: int | None
    note: str | None
    created_by_traccar_user_id: int
    created_at: datetime


class MovementListResponse(BaseModel):
    items: list[MovementOut]
    total: int
    limit: int
    offset: int
