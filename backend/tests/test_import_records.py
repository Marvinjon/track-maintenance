"""Bulk CSV import for maintenance records."""

from datetime import date

from sqlalchemy import func, select

from app.models import MaintenanceRecord, ServiceType, Vehicle
from tests.conftest import USER_A, device, mock_devices, mock_session


def _login(client, traccar_mock, device_name="Truck"):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1, name=device_name)])
    client.cookies.set("JSESSIONID", "user-a")


def _seed(db, *, plate="AB-123", device_name="Truck"):
    service_type = ServiceType(name="Oil change")
    vehicle = Vehicle(traccar_device_id=1, plate=plate)
    db.add_all([service_type, vehicle])
    db.commit()
    return service_type, vehicle


def test_import_records_by_plate(client, db, traccar_mock):
    _login(client, traccar_mock)
    _seed(db)

    response = client.post(
        "/api/v1/records/import",
        json={
            "rows": [
                {
                    "vehicle_plate": "AB-123",
                    "vehicle_device": "",
                    "service_type": "Oil change",
                    "performed_at": "2026-01-15",
                    "odometer_km": "95000",
                    "cost": "15000",
                    "currency": "ISK",
                    "performed_by": "Workshop",
                    "notes": "Routine",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["skipped"] == 0
    assert data["errors"] == []

    count = db.execute(select(func.count()).select_from(MaintenanceRecord)).scalar_one()
    assert count == 1
    record = db.execute(select(MaintenanceRecord)).scalar_one()
    assert record.performed_at == date(2026, 1, 15)
    assert record.performed_by == "Workshop"


def test_import_records_by_device_name(client, db, traccar_mock):
    _login(client, traccar_mock, device_name="Fleet Truck")
    _seed(db, plate=None, device_name="Fleet Truck")

    response = client.post(
        "/api/v1/records/import",
        json={
            "rows": [
                {
                    "vehicle_plate": "",
                    "vehicle_device": "Fleet Truck",
                    "service_type": "Oil change",
                    "performed_at": "2026-02-01",
                    "odometer_km": "",
                    "cost": "",
                    "currency": "",
                    "performed_by": "",
                    "notes": "",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["errors"] == []


def test_import_records_unknown_vehicle_error(client, db, traccar_mock):
    _login(client, traccar_mock)
    db.add(ServiceType(name="Oil change"))
    db.commit()

    response = client.post(
        "/api/v1/records/import",
        json={
            "rows": [
                {
                    "vehicle_plate": "ZZ-999",
                    "vehicle_device": "",
                    "service_type": "Oil change",
                    "performed_at": "2026-01-15",
                    "odometer_km": "",
                    "cost": "",
                    "currency": "",
                    "performed_by": "",
                    "notes": "",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 0
    assert data["errors"][0]["message"] == "Unknown vehicle"


def test_import_records_accepts_us_short_date(client, db, traccar_mock):
    _login(client, traccar_mock)
    _seed(db)

    response = client.post(
        "/api/v1/records/import",
        json={
            "rows": [
                {
                    "vehicle_plate": "AB-123",
                    "vehicle_device": "",
                    "service_type": "Oil change",
                    "performed_at": "1/15/26",
                    "odometer_km": "95000",
                    "cost": "15000",
                    "currency": "ISK",
                    "performed_by": "Workshop",
                    "notes": "",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["errors"] == []

    record = db.execute(select(MaintenanceRecord)).scalar_one()
    assert record.performed_at == date(2026, 1, 15)


def test_import_records_unknown_service_type_error(client, db, traccar_mock):
    _login(client, traccar_mock)
    db.add(Vehicle(traccar_device_id=1, plate="AB-123"))
    db.commit()

    response = client.post(
        "/api/v1/records/import",
        json={
            "rows": [
                {
                    "vehicle_plate": "AB-123",
                    "vehicle_device": "",
                    "service_type": "Missing type",
                    "performed_at": "2026-01-15",
                    "odometer_km": "",
                    "cost": "",
                    "currency": "",
                    "performed_by": "",
                    "notes": "",
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 0
    assert "Unknown service type" in data["errors"][0]["message"]
