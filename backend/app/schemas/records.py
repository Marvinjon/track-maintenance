from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.config import NOTES_MAX_LENGTH


class RecordPartIn(BaseModel):
    part_id: int
    quantity: Decimal = Field(gt=0)


class RecordPartOut(BaseModel):
    part_id: int
    part_name: str | None = None
    quantity: Decimal


class RecordCreate(BaseModel):
    service_type_id: int
    performed_at: date
    odometer_km: Decimal | None = Field(default=None, ge=0)
    cost: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="ISK", min_length=3, max_length=3)
    performed_by: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    parts: list[RecordPartIn] = []


class RecordUpdate(BaseModel):
    service_type_id: int | None = None
    performed_at: date | None = None
    odometer_km: Decimal | None = Field(default=None, ge=0)
    cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    performed_by: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    # When provided, replaces the record's parts (stock movements are
    # reversed and re-applied accordingly). Omit to leave parts unchanged.
    parts: list[RecordPartIn] | None = None


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    service_type_id: int
    service_type_name: str | None = None
    performed_at: date
    odometer_km: Decimal | None
    cost: Decimal | None
    currency: str
    performed_by: str | None
    notes: str | None
    created_by_traccar_user_id: int
    created_at: datetime
    parts: list[RecordPartOut] = []


class RecordListResponse(BaseModel):
    items: list[RecordOut]
    total: int
    limit: int
    offset: int


class RecordChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field: str
    old_value: str | None
    new_value: str | None
    changed_by_traccar_user_id: int
    created_at: datetime


class RecordDetailOut(RecordOut):
    changes: list[RecordChangeOut] = []


class RecordWithVehicleOut(RecordOut):
    vehicle_plate: str | None = None
    vehicle_device_name: str | None = None


class FleetRecordListResponse(BaseModel):
    items: list[RecordWithVehicleOut]
    total: int
    limit: int
    offset: int
