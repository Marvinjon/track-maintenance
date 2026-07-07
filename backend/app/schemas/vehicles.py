from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.config import NOTES_MAX_LENGTH
from app.schemas.records import RecordOut
from app.schemas.reminders import ReminderOut


class VehicleOut(BaseModel):
    """A Traccar device the user can see, merged with our local vehicle row.

    ``registered`` is False for devices with no local row yet — the UI offers
    "Enable maintenance tracking" for those stubs.
    """

    model_config = ConfigDict(from_attributes=True)

    registered: bool
    traccar_device_id: int
    device_name: str | None = None
    device_unique_id: str | None = None
    device_status: str | None = None

    id: int | None = None
    plate: str | None = None
    vin: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    odometer_km_cached: Decimal | None = None
    odometer_synced_at: datetime | None = None
    engine_hours_cached: Decimal | None = None
    notes: str | None = None
    archived: bool = False

    last_service_date: date | None = None
    reminder_status: str | None = None


class VehicleCreate(BaseModel):
    traccar_device_id: int
    plate: str | None = Field(default=None, max_length=20)
    vin: str | None = Field(default=None, max_length=32)
    make: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=64)
    year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    create_default_reminders: bool = False


class VehicleBulkCreate(BaseModel):
    traccar_device_ids: list[int] = Field(min_length=1, max_length=100)
    create_default_reminders: bool = False


class VehicleBulkCreateResult(BaseModel):
    created: list[VehicleOut]
    skipped: list[int]


class VehicleUpdate(BaseModel):
    plate: str | None = Field(default=None, max_length=20)
    vin: str | None = Field(default=None, max_length=32)
    make: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=64)
    year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    archived: bool | None = None


class VehicleTransfer(BaseModel):
    """Start a new maintenance profile on the same tracker."""

    plate: str | None = Field(default=None, max_length=20)
    vin: str | None = Field(default=None, max_length=32)
    make: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=64)
    year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    create_default_reminders: bool = False
    sync_odometer: bool = True


class VehicleTransferResult(BaseModel):
    archived_vehicle_id: int
    vehicle: VehicleOut


class VehicleDetail(VehicleOut):
    reminders: list[ReminderOut] = []
    recent_records: list[RecordOut] = []
