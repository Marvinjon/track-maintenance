from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ServiceTypeCostBreakdown(BaseModel):
    service_type_id: int
    service_type_name: str
    labor_cost: Decimal
    parts_cost: Decimal
    total_cost: Decimal
    record_count: int


class CostReportPartLine(BaseModel):
    part_id: int
    part_name: str
    sku: str | None
    unit: str
    quantity: Decimal
    unit_cost: Decimal | None
    line_cost: Decimal


class CostReportRecordDetail(BaseModel):
    id: int
    service_type_id: int
    service_type_name: str
    performed_at: date
    odometer_km: Decimal | None
    labor_cost: Decimal | None
    parts_cost: Decimal
    total_cost: Decimal
    currency: str
    performed_by: str | None
    notes: str | None
    parts: list[CostReportPartLine]


class CostReportPartAggregate(BaseModel):
    part_id: int
    part_name: str
    sku: str | None
    unit: str
    total_quantity: Decimal
    total_cost: Decimal


class CostReportDetailResponse(BaseModel):
    year: int
    month: int
    vehicle_id: int
    vehicle_plate: str | None
    vehicle_device_name: str | None
    currency: str
    labor_cost: Decimal
    parts_cost: Decimal
    total_cost: Decimal
    service_type_breakdown: list[ServiceTypeCostBreakdown]
    records: list[CostReportRecordDetail]
    parts_summary: list[CostReportPartAggregate]


class MonthlyCostRow(BaseModel):
    year: int
    month: int
    vehicle_id: int
    vehicle_plate: str | None
    vehicle_device_name: str | None
    currency: str
    labor_cost: Decimal
    parts_cost: Decimal
    total_cost: Decimal
    record_count: int
    km_driven: Decimal | None
    cost_per_km: Decimal | None
    hours_in_period: Decimal | None
    cost_per_hour: Decimal | None
    odometer_stale: bool
    breakdown: list[ServiceTypeCostBreakdown] = []


class CostReportSummary(BaseModel):
    total_labor_cost: Decimal
    total_parts_cost: Decimal
    total_cost: Decimal
    record_count: int
    currency: str | None


class CostReportResponse(BaseModel):
    from_date: date
    to_date: date
    summaries: list[CostReportSummary]
    rows: list[MonthlyCostRow]


class DashboardResponse(BaseModel):
    spend_this_month: Decimal
    spend_last_month: Decimal
    currency: str | None
    overdue_reminders: int
    due_soon_reminders: int
    low_stock_count: int
    recent_records: list[dict]
