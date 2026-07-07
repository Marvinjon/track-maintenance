from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReminderCreate(BaseModel):
    service_type_id: int
    interval_km: int | None = Field(default=None, gt=0)
    interval_days: int | None = Field(default=None, gt=0)
    interval_hours: int | None = Field(default=None, gt=0)
    last_service_odometer_km: Decimal | None = Field(default=None, ge=0)
    last_service_engine_hours: Decimal | None = Field(default=None, ge=0)
    last_service_date: date | None = None

    @model_validator(mode="after")
    def at_least_one_interval(self) -> "ReminderCreate":
        if (
            self.interval_km is None
            and self.interval_days is None
            and self.interval_hours is None
        ):
            raise ValueError("Provide interval_km, interval_days, and/or interval_hours")
        return self


class ReminderUpdate(BaseModel):
    interval_km: int | None = Field(default=None, gt=0)
    interval_days: int | None = Field(default=None, gt=0)
    interval_hours: int | None = Field(default=None, gt=0)
    last_service_odometer_km: Decimal | None = Field(default=None, ge=0)
    last_service_engine_hours: Decimal | None = Field(default=None, ge=0)
    last_service_date: date | None = None


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    service_type_id: int
    service_type_name: str | None = None
    traccar_maintenance_id: int | None
    traccar_maintenance_type: str | None = None
    traccar_maintenance_name: str | None = None
    interval_km: int | None
    interval_days: int | None
    interval_hours: int | None
    last_service_odometer_km: Decimal | None
    last_service_engine_hours: Decimal | None
    last_service_date: date | None
    status: str
    sync_error: bool
    created_at: datetime


class ReminderWithVehicleOut(ReminderOut):
    vehicle_plate: str | None = None
    vehicle_device_name: str | None = None
