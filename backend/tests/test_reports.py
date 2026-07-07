"""Cost reports and CSV export."""

from datetime import date
from decimal import Decimal

from app.models import MaintenanceRecord, Part, RecordPart, ServiceType, Vehicle
from tests.conftest import USER_A, device, mock_devices, mock_session


def _login(client, traccar_mock, user=USER_A, devices=(1,)):
    mock_session(traccar_mock, user)
    mock_devices(traccar_mock, [device(d) for d in devices])
    client.cookies.set("JSESSIONID", f"user-{user['id']}")


def _seed_vehicle_with_records(db):
    st = ServiceType(name="Oil change", default_interval_km=10000)
    db.add(st)
    db.flush()
    part = Part(name="Oil filter", unit_cost=Decimal("25.00"))
    db.add(part)
    db.flush()
    vehicle = Vehicle(traccar_device_id=1, plate="AB-123", odometer_km_cached=Decimal("10000"))
    db.add(vehicle)
    db.flush()
    r1 = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=st.id,
        performed_at=date(2026, 1, 15),
        odometer_km=Decimal("9500"),
        cost=Decimal("100.00"),
        currency="ISK",
        created_by_traccar_user_id=USER_A["id"],
    )
    r2 = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=st.id,
        performed_at=date(2026, 2, 10),
        odometer_km=Decimal("10000"),
        cost=Decimal("150.00"),
        currency="ISK",
        created_by_traccar_user_id=USER_A["id"],
    )
    r3 = MaintenanceRecord(
        vehicle_id=vehicle.id,
        service_type_id=st.id,
        performed_at=date(2026, 2, 20),
        odometer_km=Decimal("10500"),
        cost=Decimal("50.00"),
        currency="ISK",
        created_by_traccar_user_id=USER_A["id"],
    )
    db.add_all([r1, r2, r3])
    db.flush()
    db.add(RecordPart(maintenance_record_id=r1.id, part_id=part.id, quantity=Decimal("1")))
    db.add(RecordPart(maintenance_record_id=r2.id, part_id=part.id, quantity=Decimal("2")))
    db.add(RecordPart(maintenance_record_id=r3.id, part_id=part.id, quantity=Decimal("1")))
    db.commit()
    return vehicle, st


def test_cost_report_groups_by_month(client, db, traccar_mock):
    _login(client, traccar_mock, devices=(1,))
    _seed_vehicle_with_records(db)

    response = client.get(
        "/api/v1/reports/costs",
        params={"from": "2026-01-01", "to": "2026-02-28"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["from_date"] == "2026-01-01"
    assert len(body["rows"]) == 2
    jan = next(r for r in body["rows"] if r["month"] == 1)
    assert jan["labor_cost"] == "100.00"
    assert jan["parts_cost"] == "25.00"
    assert jan["total_cost"] == "125.00"
    assert jan["record_count"] == 1
    assert jan["km_driven"] is None  # only one record in January
    feb = next(r for r in body["rows"] if r["month"] == 2)
    # Feb: labor 200 + parts 75 = 275; km 10000->10500 = 500
    assert feb["total_cost"] == "275.00"
    assert feb["cost_per_km"] == "0.55"


def test_cost_per_km_uses_prior_month_odometer(client, db, traccar_mock):
    _login(client, traccar_mock, devices=(1,))
    vehicle, st = _seed_vehicle_with_records(db)
    db.add(
        MaintenanceRecord(
            vehicle_id=vehicle.id,
            service_type_id=st.id,
            performed_at=date(2026, 3, 5),
            odometer_km=Decimal("11000"),
            cost=Decimal("0"),
            currency="ISK",
            created_by_traccar_user_id=USER_A["id"],
        )
    )
    db.commit()

    response = client.get(
        "/api/v1/reports/costs",
        params={"from": "2026-03-01", "to": "2026-03-31"},
    )
    assert response.status_code == 200
    march = response.json()["rows"][0]
    assert march["km_driven"] == "500.0"  # 11000 - 10500 (last Feb record)
    assert march["cost_per_km"] == "0.00"


def test_cost_report_tenant_isolation(client, db, traccar_mock):
    from tests.conftest import USER_B

    _seed_vehicle_with_records(db)
    mock_session(traccar_mock, USER_B)
    mock_devices(traccar_mock, [])
    client.cookies.set("JSESSIONID", f"user-{USER_B['id']}")

    response = client.get(
        "/api/v1/reports/costs",
        params={"from": "2026-01-01", "to": "2026-02-28"},
    )
    assert response.status_code == 200
    assert response.json()["rows"] == []


def test_csv_export(client, db, traccar_mock):
    _login(client, traccar_mock, devices=(1,))
    _seed_vehicle_with_records(db)

    response = client.get(
        "/api/v1/reports/records/export",
        params={"from": "2026-01-01", "to": "2026-02-28"},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().split("\n")
    assert len(lines) == 4  # header + 3 records
    assert "AB-123" in lines[1]


def test_dashboard(client, db, traccar_mock):
    _login(client, traccar_mock, devices=(1,))
    _seed_vehicle_with_records(db)

    response = client.get("/api/v1/reports/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert "spend_this_month" in body
    assert "recent_records" in body


def test_bulk_create_vehicles(client, traccar_mock, db):
    _login(client, traccar_mock, devices=(1, 2))

    response = client.post(
        "/api/v1/vehicles/bulk",
        json={"traccar_device_ids": [1, 2], "create_default_reminders": False},
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["created"]) == 2
    assert body["skipped"] == []


def test_cost_report_detail(client, db, traccar_mock):
    _login(client, traccar_mock, devices=(1,))
    _seed_vehicle_with_records(db)

    response = client.get(
        "/api/v1/reports/costs/detail",
        params={"vehicle_id": 1, "year": 2026, "month": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["records"]) >= 2
    assert body["parts_summary"]
    assert body["service_type_breakdown"]
    feb_record = next(r for r in body["records"] if r["parts"])
    assert len(feb_record["parts"]) >= 1
    assert feb_record["parts"][0]["line_cost"] is not None


def test_cost_report_detail_not_found(client, traccar_mock):
    _login(client, traccar_mock, devices=(1,))
    response = client.get(
        "/api/v1/reports/costs/detail",
        params={"vehicle_id": 1, "year": 2020, "month": 1},
    )
    assert response.status_code == 404


def test_create_vehicle_with_default_reminders(client, db, traccar_mock):
    _login(client, traccar_mock, devices=(1,))
    db.add(ServiceType(name="Oil change", default_interval_km=10000))
    db.commit()

    response = client.post(
        "/api/v1/vehicles",
        json={"traccar_device_id": 1, "create_default_reminders": True},
    )
    assert response.status_code == 201
    vehicle_id = response.json()["id"]
    reminders = client.get(f"/api/v1/vehicles/{vehicle_id}/reminders")
    assert reminders.status_code == 200
    assert len(reminders.json()) == 1
