"""Vehicles CRUD + on-demand odometer sync."""

from app.models import ServiceType, Vehicle
from tests.conftest import (
    USER_A,
    device,
    mock_devices,
    mock_positions,
    mock_session,
    position,
)


def _login(client, traccar_mock, devices):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, devices)
    client.cookies.set("JSESSIONID", "user-a")


def test_create_vehicle_for_visible_device(client, traccar_mock):
    _login(client, traccar_mock, [device(1)])

    response = client.post(
        "/api/v1/vehicles",
        json={"traccar_device_id": 1, "plate": "AB-123", "make": "Toyota"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["registered"] is True
    assert body["plate"] == "AB-123"
    assert body["device_name"] == "Truck"


def test_create_vehicle_for_invisible_device_404(client, traccar_mock):
    _login(client, traccar_mock, [device(1)])

    response = client.post("/api/v1/vehicles", json={"traccar_device_id": 99})

    assert response.status_code == 404


def test_create_duplicate_vehicle_409(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    db.add(Vehicle(traccar_device_id=1))
    db.commit()

    response = client.post("/api/v1/vehicles", json={"traccar_device_id": 1})

    assert response.status_code == 409


def test_create_vehicle_after_archived_device_allowed(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    archived = Vehicle(traccar_device_id=1, plate="OLD-1", archived=True)
    db.add(archived)
    db.commit()

    response = client.post(
        "/api/v1/vehicles",
        json={"traccar_device_id": 1, "plate": "NEW-1"},
    )

    assert response.status_code == 201
    assert response.json()["plate"] == "NEW-1"


def test_transfer_tracker_archives_old_and_creates_new(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1, plate="SOLD-1", make="Volvo")
    db.add(vehicle)
    db.commit()
    old_id = vehicle.id

    response = client.post(
        f"/api/v1/vehicles/{old_id}/transfer",
        json={"plate": "NEW-99", "make": "Scania", "sync_odometer": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["archived_vehicle_id"] == old_id
    assert body["vehicle"]["plate"] == "NEW-99"
    assert body["vehicle"]["make"] == "Scania"
    assert body["vehicle"]["id"] != old_id

    db.expire_all()
    old_row = db.get(Vehicle, old_id)
    new_row = db.get(Vehicle, body["vehicle"]["id"])
    assert old_row.archived is True
    assert new_row.archived is False
    assert old_row.traccar_device_id == new_row.traccar_device_id == 1

    listed = client.get("/api/v1/vehicles").json()
    assert len(listed) == 1
    assert listed[0]["registered"] is True
    assert listed[0]["plate"] == "NEW-99"
    assert listed[0]["id"] == new_row.id


def test_transfer_archived_vehicle_422(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1, archived=True)
    db.add(vehicle)
    db.commit()

    response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/transfer",
        json={"plate": "X"},
    )

    assert response.status_code == 422


def test_get_vehicle_detail(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1, plate="AB-123")
    db.add(vehicle)
    db.commit()

    response = client.get(f"/api/v1/vehicles/{vehicle.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["plate"] == "AB-123"
    assert body["reminders"] == []
    assert body["recent_records"] == []


def test_get_vehicle_detail_denied_for_other_tenant(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])  # user sees only device 1
    vehicle = Vehicle(traccar_device_id=42)  # belongs to another tenant
    db.add(vehicle)
    db.commit()

    response = client.get(f"/api/v1/vehicles/{vehicle.id}")

    assert response.status_code == 404


def test_patch_vehicle(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    response = client.patch(
        f"/api/v1/vehicles/{vehicle.id}", json={"plate": "XY-999", "year": 2020}
    )

    assert response.status_code == 200
    assert response.json()["plate"] == "XY-999"
    assert response.json()["year"] == 2020


def test_delete_vehicle_is_soft_archive(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    response = client.delete(f"/api/v1/vehicles/{vehicle.id}")
    assert response.status_code == 204

    db.expire_all()
    row = db.get(Vehicle, vehicle.id)
    assert row is not None  # row kept
    assert row.archived is True


def test_sync_odometer_converts_units(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    # totalDistance in meters, hours in milliseconds.
    mock_positions(
        traccar_mock,
        {1: [position(1, totalDistance=123_456_789, hours=5_400_000)]},
    )

    response = client.post(f"/api/v1/vehicles/{vehicle.id}/sync-odometer")

    assert response.status_code == 200
    body = response.json()
    assert float(body["odometer_km_cached"]) == 123456.8
    assert float(body["engine_hours_cached"]) == 1.5
    assert body["odometer_synced_at"] is not None


def test_sync_odometer_falls_back_to_odometer_attribute(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    mock_positions(traccar_mock, {1: [position(1, odometer=50_000_000)]})

    response = client.post(f"/api/v1/vehicles/{vehicle.id}/sync-odometer")

    assert response.status_code == 200
    assert float(response.json()["odometer_km_cached"]) == 50000.0


def test_sync_odometer_uses_admin_token(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    positions_route = mock_positions(
        traccar_mock, {1: [position(1, totalDistance=1000)]}
    )

    client.post(f"/api/v1/vehicles/{vehicle.id}/sync-odometer")

    auth_header = positions_route.calls.last.request.headers.get("authorization")
    assert auth_header == "Bearer admin-test-token"


def test_sync_odometer_no_position_404(client, db, traccar_mock):
    _login(client, traccar_mock, [device(1)])
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    mock_positions(traccar_mock, {})

    response = client.post(f"/api/v1/vehicles/{vehicle.id}/sync-odometer")

    assert response.status_code == 404


def test_list_service_types(client, db, traccar_mock):
    _login(client, traccar_mock, [])
    db.add(ServiceType(name="Oil change", default_interval_km=15000))
    db.commit()

    response = client.get("/api/v1/service-types")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Oil change"
