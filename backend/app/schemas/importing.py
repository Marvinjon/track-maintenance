from pydantic import BaseModel, Field

from app.config import NOTES_MAX_LENGTH

MAX_IMPORT_ROWS = 500


class ImportRowError(BaseModel):
    row: int
    message: str


class ImportResult(BaseModel):
    created: int
    skipped: int
    errors: list[ImportRowError]


class ServiceTypeImportRow(BaseModel):
    name: str = ""
    default_interval_km: str = ""
    default_interval_days: str = ""


class ServiceTypeImportRequest(BaseModel):
    rows: list[ServiceTypeImportRow] = Field(max_length=MAX_IMPORT_ROWS)


class PartImportRow(BaseModel):
    sku: str = ""
    name: str = ""
    unit: str = ""
    min_stock: str = ""
    unit_cost: str = ""
    initial_stock: str = ""


class PartImportRequest(BaseModel):
    rows: list[PartImportRow] = Field(max_length=MAX_IMPORT_ROWS)


class RecordImportRow(BaseModel):
    vehicle_plate: str = ""
    vehicle_device: str = ""
    service_type: str = ""
    performed_at: str = ""
    odometer_km: str = ""
    cost: str = ""
    currency: str = ""
    performed_by: str = ""
    notes: str = Field(default="", max_length=NOTES_MAX_LENGTH)


class RecordImportRequest(BaseModel):
    rows: list[RecordImportRow] = Field(max_length=MAX_IMPORT_ROWS)
