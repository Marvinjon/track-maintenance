import csv
import io
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.records import parts_by_record
from app.db import get_db
from app.models import MaintenanceRecord, Part, ServiceType, Vehicle
from app.services.vehicles import visible_vehicles
from app.schemas.records import RecordPartOut
from app.schemas.reports import (
    CostReportDetailResponse,
    CostReportResponse,
    DashboardResponse,
)
from app.services.reports import (
    build_cost_report,
    build_cost_report_detail,
    current_month_range,
    parts_cost_subquery,
    previous_month_range,
    record_costs_query,
    spend_for_period,
)
from app.services.tenant_scope import catalog_visibility_filter
from app.services.stock import current_stock_map
from app.services.traccar import TraccarService, get_traccar

router = APIRouter(prefix="/reports", tags=["reports"])


async def _visible_vehicles(
    ctx: CurrentUser,
    db: Session,
    traccar: TraccarService,
    *,
    active_only: bool = False,
) -> tuple[list[Vehicle], dict[int, str | None]]:
    devices = await traccar.as_user(ctx.credential).list_devices()
    device_ids = [d["id"] for d in devices]
    device_names = {d["id"]: d.get("name") for d in devices}
    if not device_ids:
        return [], device_names
    vehicles = visible_vehicles(db, device_ids, active_only=active_only)
    return vehicles, device_names


@router.get("/costs", response_model=CostReportResponse)
async def get_cost_report(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    vehicle_id: int | None = None,
) -> CostReportResponse:
    """Total maintenance cost per vehicle per month, with parts rollup."""
    vehicles, device_names = await _visible_vehicles(ctx, db, traccar)
    if vehicle_id is not None:
        vehicles = [v for v in vehicles if v.id == vehicle_id]
    data = build_cost_report(
        db, vehicles, device_names, from_date, to_date, vehicle_id
    )
    return CostReportResponse(**data)


@router.get("/costs/detail", response_model=CostReportDetailResponse)
async def get_cost_report_detail(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
    vehicle_id: int,
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
) -> CostReportDetailResponse:
    """Drill-down: every service record and parts line for a vehicle/month."""
    vehicles, device_names = await _visible_vehicles(ctx, db, traccar)
    vehicle = next((v for v in vehicles if v.id == vehicle_id), None)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    data = build_cost_report_detail(
        db, vehicle, device_names.get(vehicle.traccar_device_id), year, month
    )
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No records for this vehicle in the selected month",
        )
    return CostReportDetailResponse(**data)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
) -> DashboardResponse:
    from app.models import Reminder, ReminderStatus

    vehicles, device_names = await _visible_vehicles(ctx, db, traccar)
    active_vehicles, _ = await _visible_vehicles(ctx, db, traccar, active_only=True)
    vehicle_ids = [v.id for v in vehicles]
    active_vehicle_ids = [v.id for v in active_vehicles]

    this_start, this_end = current_month_range()
    last_start, last_end = previous_month_range()
    spend_this, currency = spend_for_period(db, vehicle_ids, this_start, this_end)
    spend_last, last_currency = spend_for_period(db, vehicle_ids, last_start, last_end)
    if currency is None:
        currency = last_currency

    overdue = due_soon = 0
    low_stock_count = 0
    if active_vehicle_ids:
        for status, count in db.execute(
            select(Reminder.status, func.count())
            .where(Reminder.vehicle_id.in_(active_vehicle_ids))
            .group_by(Reminder.status)
        ):
            if status == ReminderStatus.overdue:
                overdue = count
            elif status == ReminderStatus.due_soon:
                due_soon = count

    parts = db.execute(
        select(Part).where(
            Part.archived.is_(False),
            catalog_visibility_filter(Part.traccar_tenant_user_id, ctx.tenant_user_id),
        )
    ).scalars().all()
    if parts:
        stocks = current_stock_map(db, [p.id for p in parts])
        low_stock_count = sum(
            1 for p in parts if stocks.get(p.id, 0) < p.min_stock
        )

    recent_records: list[dict] = []
    if vehicle_ids:
        rows = db.execute(
            select(MaintenanceRecord, ServiceType.name, Vehicle)
            .join(ServiceType, MaintenanceRecord.service_type_id == ServiceType.id)
            .join(Vehicle, MaintenanceRecord.vehicle_id == Vehicle.id)
            .where(MaintenanceRecord.vehicle_id.in_(vehicle_ids))
            .order_by(MaintenanceRecord.performed_at.desc(), MaintenanceRecord.id.desc())
            .limit(5)
        ).all()
        parts_map = parts_by_record(db, [r.id for r, _, _ in rows])
        for record, st_name, vehicle in rows:
            recent_records.append(
                {
                    "id": record.id,
                    "vehicle_id": record.vehicle_id,
                    "vehicle_plate": vehicle.plate,
                    "vehicle_device_name": device_names.get(vehicle.traccar_device_id),
                    "service_type_name": st_name,
                    "performed_at": record.performed_at.isoformat(),
                    "cost": str(record.cost) if record.cost is not None else None,
                    "currency": record.currency,
                    "parts": [
                        RecordPartOut(
                            part_id=p.part_id,
                            part_name=p.part_name,
                            quantity=p.quantity,
                        ).model_dump()
                        for p in parts_map.get(record.id, [])
                    ],
                }
            )

    return DashboardResponse(
        spend_this_month=spend_this,
        spend_last_month=spend_last,
        currency=currency,
        overdue_reminders=overdue,
        due_soon_reminders=due_soon,
        low_stock_count=low_stock_count,
        recent_records=recent_records,
    )


@router.get("/records/export")
async def export_records_csv(
    ctx: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    traccar: Annotated[TraccarService, Depends(get_traccar)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    vehicle_id: int | None = None,
) -> StreamingResponse:
    """One row per maintenance record for accounting export."""
    vehicles, device_names = await _visible_vehicles(ctx, db, traccar)
    vehicle_ids = [v.id for v in vehicles]
    vehicles_by_id = {v.id: v for v in vehicles}
    if vehicle_id is not None:
        if vehicle_id not in vehicle_ids:
            vehicle_ids = []
        else:
            vehicle_ids = [vehicle_id]

    rows = record_costs_query(db, vehicle_ids, from_date, to_date, vehicle_id) if vehicle_ids else []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "date",
            "vehicle_plate",
            "vehicle_device",
            "service_type",
            "odometer_km",
            "labor_cost",
            "parts_cost",
            "total_cost",
            "currency",
            "performed_by",
            "notes",
        ]
    )
    for row in rows:
        vehicle = vehicles_by_id[row.vehicle_id]
        labor = row.cost or Decimal("0")
        parts = Decimal(str(row.parts_cost))
        record = db.get(MaintenanceRecord, row.id)
        writer.writerow(
            [
                row.performed_at.isoformat(),
                vehicle.plate or "",
                device_names.get(vehicle.traccar_device_id) or "",
                row.service_type_name,
                str(row.odometer_km) if row.odometer_km is not None else "",
                str(labor),
                str(parts),
                str(labor + parts),
                row.currency,
                record.performed_by if record else "",
                record.notes if record else "",
            ]
        )

    output.seek(0)
    filename = f"maintenance-records-{from_date}-{to_date}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
