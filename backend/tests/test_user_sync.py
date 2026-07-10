"""Per-user Traccar sync on login and session restore."""

from httpx import Response

from app.models import Vehicle
from tests.conftest import (
    TRACCAR,
    USER_A,
    device,
    mock_devices,
    mock_positions,
    mock_session,
    position,
)


def test_login_syncs_odometer_for_visible_vehicles(client, db, traccar_mock):
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    traccar_mock.post(f"{TRACCAR}/api/session").mock(
        return_value=Response(
            200,
            json=USER_A,
            headers={"set-cookie": "JSESSIONID=logged-in; Path=/api"},
        )
    )
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    mock_positions(traccar_mock, {1: [position(1, totalDistance=123_450)]})

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "secret"},
    )
    assert response.status_code == 200

    db.expire_all()
    row = db.get(Vehicle, vehicle.id)
    assert row is not None
    assert float(row.odometer_km_cached) == 123.5
    assert row.odometer_synced_at is not None


def test_me_syncs_odometer_for_visible_vehicles(client, db, traccar_mock):
    vehicle = Vehicle(traccar_device_id=1)
    db.add(vehicle)
    db.commit()

    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    mock_positions(traccar_mock, {1: [position(1, totalDistance=50_000)]})

    client.cookies.set("maint_session", "user-a")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200

    db.expire_all()
    row = db.get(Vehicle, vehicle.id)
    assert row is not None
    assert float(row.odometer_km_cached) == 50.0
