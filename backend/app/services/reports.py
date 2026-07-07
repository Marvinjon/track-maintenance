"""Cost reporting queries — tenant-scoped via visible Traccar devices."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import MaintenanceRecord, Part, RecordPart, ServiceType, Vehicle


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parts_cost_subquery():
    """Per-record parts cost: SUM(quantity * unit_cost)."""
    return (
        select(
            RecordPart.maintenance_record_id.label("record_id"),
            func.coalesce(
                func.sum(RecordPart.quantity * func.coalesce(Part.unit_cost, 0)), 0
            ).label("parts_cost"),
        )
        .join(Part, RecordPart.part_id == Part.id)
        .group_by(RecordPart.maintenance_record_id)
        .subquery()
    )


def record_costs_query(
    db: Session,
    vehicle_ids: list[int],
    from_date: date,
    to_date: date,
    vehicle_id: int | None = None,
):
    """Base query: one row per maintenance record with labor + parts cost."""
    parts_sq = parts_cost_subquery()
    filters = [
        MaintenanceRecord.vehicle_id.in_(vehicle_ids),
        MaintenanceRecord.performed_at >= from_date,
        MaintenanceRecord.performed_at <= to_date,
    ]
    if vehicle_id is not None:
        filters.append(MaintenanceRecord.vehicle_id == vehicle_id)

    return db.execute(
        select(
            MaintenanceRecord.id,
            MaintenanceRecord.vehicle_id,
            MaintenanceRecord.service_type_id,
            ServiceType.name.label("service_type_name"),
            MaintenanceRecord.performed_at,
            MaintenanceRecord.odometer_km,
            MaintenanceRecord.cost,
            MaintenanceRecord.currency,
            func.coalesce(parts_sq.c.parts_cost, 0).label("parts_cost"),
        )
        .join(ServiceType, MaintenanceRecord.service_type_id == ServiceType.id)
        .outerjoin(parts_sq, parts_sq.c.record_id == MaintenanceRecord.id)
        .where(and_(*filters))
        .order_by(MaintenanceRecord.performed_at, MaintenanceRecord.id)
    ).all()


def _km_driven_for_records(
    db: Session,
    vehicle_id: int,
    records: list[Any],
    period_start: date,
) -> Decimal | None:
    """Km between min/max odometer in the period, using a prior service as baseline."""
    odometers = [
        Decimal(str(r.odometer_km))
        for r in records
        if r.odometer_km is not None
    ]
    if not odometers:
        return None

    if len(odometers) >= 2:
        delta = max(odometers) - min(odometers)
        return delta if delta > 0 else None

    baseline = db.execute(
        select(MaintenanceRecord.odometer_km)
        .where(
            MaintenanceRecord.vehicle_id == vehicle_id,
            MaintenanceRecord.performed_at < period_start,
            MaintenanceRecord.odometer_km.is_not(None),
        )
        .order_by(MaintenanceRecord.performed_at.desc(), MaintenanceRecord.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if baseline is None:
        return None

    delta = odometers[0] - Decimal(str(baseline))
    return delta if delta > 0 else None


def _hours_in_period(vehicle: Vehicle, from_date: date, to_date: date) -> Decimal | None:
    if vehicle.engine_hours_cached is None:
        return None
    # Without historical snapshots, use cached hours as period upper bound when
    # the vehicle has records in range (approximate lifetime-to-date metric).
    return Decimal(str(vehicle.engine_hours_cached))


def _odometer_stale(vehicle: Vehicle, stale_days: int = 7) -> bool:
    if vehicle.odometer_synced_at is None:
        return True
    cutoff = _utcnow_naive() - timedelta(days=stale_days)
    return vehicle.odometer_synced_at < cutoff


def build_cost_report(
    db: Session,
    vehicles: list[Vehicle],
    device_names: dict[int, str | None],
    from_date: date,
    to_date: date,
    vehicle_id: int | None = None,
    include_breakdown: bool = True,
) -> dict:
    vehicle_ids = [v.id for v in vehicles]
    vehicles_by_id = {v.id: v for v in vehicles}
    if not vehicle_ids:
        return {
            "from_date": from_date,
            "to_date": to_date,
            "summaries": [],
            "rows": [],
        }

    rows_data = record_costs_query(db, vehicle_ids, from_date, to_date, vehicle_id)

    # Group: (vehicle_id, year, month, currency)
    grouped: dict[tuple, list] = {}
    for row in rows_data:
        key = (row.vehicle_id, row.performed_at.year, row.performed_at.month, row.currency)
        grouped.setdefault(key, []).append(row)

    report_rows = []
    summary_by_currency: dict[str, dict] = {}

    for (vid, year, month, currency), records in sorted(grouped.items()):
        vehicle = vehicles_by_id[vid]
        labor = sum((r.cost or Decimal("0")) for r in records)
        parts = sum(Decimal(str(r.parts_cost)) for r in records)
        total = labor + parts
        km_driven = _km_driven_for_records(
            db, vid, records, date(year, month, 1)
        )
        hours = _hours_in_period(vehicle, from_date, to_date)
        cost_per_km = (total / km_driven).quantize(Decimal("0.01")) if km_driven else None
        cost_per_hour = (
            (total / hours).quantize(Decimal("0.01"))
            if hours and hours > 0 and vehicle.engine_hours_cached
            else None
        )

        breakdown = []
        if include_breakdown:
            by_type: dict[int, list] = {}
            for r in records:
                by_type.setdefault(r.service_type_id, []).append(r)
            for st_id, type_records in by_type.items():
                t_labor = sum((r.cost or Decimal("0")) for r in type_records)
                t_parts = sum(Decimal(str(r.parts_cost)) for r in type_records)
                breakdown.append(
                    {
                        "service_type_id": st_id,
                        "service_type_name": type_records[0].service_type_name,
                        "labor_cost": t_labor,
                        "parts_cost": t_parts,
                        "total_cost": t_labor + t_parts,
                        "record_count": len(type_records),
                    }
                )

        report_rows.append(
            {
                "year": year,
                "month": month,
                "vehicle_id": vid,
                "vehicle_plate": vehicle.plate,
                "vehicle_device_name": device_names.get(vehicle.traccar_device_id),
                "currency": currency,
                "labor_cost": labor,
                "parts_cost": parts,
                "total_cost": total,
                "record_count": len(records),
                "km_driven": km_driven,
                "cost_per_km": cost_per_km,
                "hours_in_period": hours,
                "cost_per_hour": cost_per_hour,
                "odometer_stale": _odometer_stale(vehicle),
                "breakdown": breakdown,
            }
        )

        s = summary_by_currency.setdefault(
            currency,
            {
                "total_labor_cost": Decimal("0"),
                "total_parts_cost": Decimal("0"),
                "total_cost": Decimal("0"),
                "record_count": 0,
                "currency": currency,
            },
        )
        s["total_labor_cost"] += labor
        s["total_parts_cost"] += parts
        s["total_cost"] += total
        s["record_count"] += len(records)

    summaries = list(summary_by_currency.values())
    if len(summaries) == 1:
        pass
    elif not summaries:
        summaries = []

    return {
        "from_date": from_date,
        "to_date": to_date,
        "summaries": summaries,
        "rows": report_rows,
    }


def month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def current_month_range() -> tuple[date, date]:
    today = date.today()
    return month_range(today.year, today.month)


def previous_month_range() -> tuple[date, date]:
    today = date.today()
    if today.month == 1:
        return month_range(today.year - 1, 12)
    return month_range(today.year, today.month - 1)


def spend_for_period(
    db: Session,
    vehicle_ids: list[int],
    from_date: date,
    to_date: date,
) -> tuple[Decimal, str | None]:
    if not vehicle_ids:
        return Decimal("0"), None
    rows = record_costs_query(db, vehicle_ids, from_date, to_date)
    if not rows:
        return Decimal("0"), None
    total = sum(
        (r.cost or Decimal("0")) + Decimal(str(r.parts_cost)) for r in rows
    )
    currencies = {r.currency for r in rows}
    currency = currencies.pop() if len(currencies) == 1 else None
    return total, currency


def _parts_for_records(db: Session, record_ids: list[int]) -> dict[int, list[dict]]:
    if not record_ids:
        return {}
    rows = db.execute(
        select(RecordPart, Part)
        .join(Part, RecordPart.part_id == Part.id)
        .where(RecordPart.maintenance_record_id.in_(record_ids))
        .order_by(RecordPart.maintenance_record_id, Part.name)
    ).all()
    result: dict[int, list[dict]] = {}
    for record_part, part in rows:
        unit_cost = part.unit_cost
        line_cost = record_part.quantity * (unit_cost or Decimal("0"))
        result.setdefault(record_part.maintenance_record_id, []).append(
            {
                "part_id": part.id,
                "part_name": part.name,
                "sku": part.sku,
                "unit": part.unit,
                "quantity": record_part.quantity,
                "unit_cost": unit_cost,
                "line_cost": line_cost,
            }
        )
    return result


def build_cost_report_detail(
    db: Session,
    vehicle: Vehicle,
    device_name: str | None,
    year: int,
    month: int,
) -> dict | None:
    """All service records and parts for one vehicle in a calendar month."""
    start, end = month_range(year, month)
    rows = record_costs_query(db, [vehicle.id], start, end, vehicle.id)
    if not rows:
        return None

    record_ids = [r.id for r in rows]
    full_records = {
        r.id: r
        for r in db.execute(
            select(MaintenanceRecord).where(MaintenanceRecord.id.in_(record_ids))
        ).scalars()
    }
    parts_map = _parts_for_records(db, record_ids)

    currency = rows[0].currency
    labor_total = Decimal("0")
    parts_total = Decimal("0")
    records_out: list[dict] = []
    by_type: dict[int, list] = {}
    part_agg: dict[int, dict] = {}

    for row in rows:
        record = full_records[row.id]
        labor = record.cost or Decimal("0")
        parts_cost = Decimal(str(row.parts_cost))
        labor_total += labor
        parts_total += parts_cost
        part_lines = parts_map.get(row.id, [])
        records_out.append(
            {
                "id": row.id,
                "service_type_id": row.service_type_id,
                "service_type_name": row.service_type_name,
                "performed_at": row.performed_at,
                "odometer_km": row.odometer_km,
                "labor_cost": record.cost,
                "parts_cost": parts_cost,
                "total_cost": labor + parts_cost,
                "currency": row.currency,
                "performed_by": record.performed_by,
                "notes": record.notes,
                "parts": part_lines,
            }
        )
        by_type.setdefault(row.service_type_id, []).append(row)
        for pl in part_lines:
            agg = part_agg.setdefault(
                pl["part_id"],
                {
                    "part_id": pl["part_id"],
                    "part_name": pl["part_name"],
                    "sku": pl["sku"],
                    "unit": pl["unit"],
                    "total_quantity": Decimal("0"),
                    "total_cost": Decimal("0"),
                },
            )
            agg["total_quantity"] += pl["quantity"]
            agg["total_cost"] += pl["line_cost"]

    breakdown = []
    for st_id, type_rows in by_type.items():
        t_labor = sum((full_records[r.id].cost or Decimal("0")) for r in type_rows)
        t_parts = sum(Decimal(str(r.parts_cost)) for r in type_rows)
        breakdown.append(
            {
                "service_type_id": st_id,
                "service_type_name": type_rows[0].service_type_name,
                "labor_cost": t_labor,
                "parts_cost": t_parts,
                "total_cost": t_labor + t_parts,
                "record_count": len(type_rows),
            }
        )

    return {
        "year": year,
        "month": month,
        "vehicle_id": vehicle.id,
        "vehicle_plate": vehicle.plate,
        "vehicle_device_name": device_name,
        "currency": currency,
        "labor_cost": labor_total,
        "parts_cost": parts_total,
        "total_cost": labor_total + parts_total,
        "service_type_breakdown": breakdown,
        "records": records_out,
        "parts_summary": sorted(part_agg.values(), key=lambda p: p["part_name"]),
    }
