"""Maintenance record CRUD, pagination, and tenant isolation."""

import json

import pytest

from app.models import ServiceType, Vehicle
from tests.conftest import USER_A, USER_B, device, mock_accumulators_update, mock_devices, mock_session


@pytest.fixture
def vehicle(db):
    v = Vehicle(traccar_device_id=1, plate="AB-123")
    db.add(v)
    db.add(ServiceType(name="Oil change", default_interval_km=15000))
    db.commit()
    return v


@pytest.fixture
def service_type_id(db):
    from sqlalchemy import select

    return db.execute(select(ServiceType.id)).scalar_one()


def _login(client, traccar_mock, user=USER_A, devices=(1,)):
    mock_session(traccar_mock, user)
    mock_devices(traccar_mock, [device(d) for d in devices])
    client.cookies.set("JSESSIONID", f"user-{user['id']}")


def test_create_record(client, traccar_mock, vehicle, service_type_id):
    _login(client, traccar_mock)

    response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={
            "service_type_id": service_type_id,
            "performed_at": "2026-07-01",
            "odometer_km": "123456.8",
            "cost": "45000",
            "performed_by": "Workshop X",
            "notes": "Full synthetic",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["service_type_name"] == "Oil change"
    assert body["created_by_traccar_user_id"] == USER_A["id"]
    assert body["currency"] == "ISK"
    assert float(body["odometer_km"]) == 123456.8


def test_create_record_pushes_odometer_to_traccar(client, db, traccar_mock, vehicle, service_type_id):
    _login(client, traccar_mock)
    accumulators = mock_accumulators_update(traccar_mock)

    response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={
            "service_type_id": service_type_id,
            "performed_at": "2026-07-01",
            "odometer_km": "123456.8",
        },
    )

    assert response.status_code == 201
    assert accumulators.call_count == 1
    payload = json.loads(accumulators.calls.last.request.content)
    assert payload == {"deviceId": 1, "totalDistance": 123_456_800.0}

    db.refresh(vehicle)
    assert float(vehicle.odometer_km_cached) == 123456.8
    assert vehicle.odometer_synced_at is not None


def test_create_record_unknown_service_type_422(client, traccar_mock, vehicle):
    _login(client, traccar_mock)

    response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={"service_type_id": 9999, "performed_at": "2026-07-01"},
    )

    assert response.status_code == 422


def test_list_records_newest_first_and_paginated(
    client, traccar_mock, vehicle, service_type_id
):
    _login(client, traccar_mock)

    for day in ("2026-01-05", "2026-03-10", "2026-06-20"):
        client.post(
            f"/api/v1/vehicles/{vehicle.id}/records",
            json={"service_type_id": service_type_id, "performed_at": day},
        )

    response = client.get(f"/api/v1/vehicles/{vehicle.id}/records?limit=2&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert [r["performed_at"] for r in body["items"]] == ["2026-06-20", "2026-03-10"]

    page_two = client.get(f"/api/v1/vehicles/{vehicle.id}/records?limit=2&offset=2").json()
    assert [r["performed_at"] for r in page_two["items"]] == ["2026-01-05"]


def test_update_record(client, traccar_mock, vehicle, service_type_id):
    _login(client, traccar_mock)
    record_id = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={"service_type_id": service_type_id, "performed_at": "2026-07-01"},
    ).json()["id"]

    response = client.patch(
        f"/api/v1/records/{record_id}",
        json={"cost": "12000", "performed_by": "Workshop Y"},
    )

    assert response.status_code == 200
    assert float(response.json()["cost"]) == 12000
    assert response.json()["performed_by"] == "Workshop Y"


def test_update_record_logs_change_history(client, traccar_mock, vehicle, service_type_id):
    _login(client, traccar_mock)
    record_id = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={
            "service_type_id": service_type_id,
            "performed_at": "2026-07-01",
            "cost": "5000",
        },
    ).json()["id"]

    response = client.patch(
        f"/api/v1/records/{record_id}",
        json={"cost": "6000", "performed_by": "Workshop Y"},
    )
    assert response.status_code == 200

    detail = client.get(f"/api/v1/records/{record_id}").json()
    assert len(detail["changes"]) == 2
    by_field = {change["field"]: change for change in detail["changes"]}
    assert by_field["cost"]["old_value"] == "5000"
    assert by_field["cost"]["new_value"] == "6000"
    assert by_field["performed_by"]["old_value"] is None
    assert by_field["performed_by"]["new_value"] == "Workshop Y"


def test_update_record_skips_unchanged_fields(client, traccar_mock, vehicle, service_type_id):
    _login(client, traccar_mock)
    record_id = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={
            "service_type_id": service_type_id,
            "performed_at": "2026-07-01",
            "cost": "5000",
        },
    ).json()["id"]

    client.patch(f"/api/v1/records/{record_id}", json={"cost": "5000"})

    detail = client.get(f"/api/v1/records/{record_id}").json()
    assert detail["changes"] == []


def test_delete_record(client, traccar_mock, vehicle, service_type_id):
    _login(client, traccar_mock)
    record_id = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={"service_type_id": service_type_id, "performed_at": "2026-07-01"},
    ).json()["id"]

    assert client.delete(f"/api/v1/records/{record_id}").status_code == 204
    assert client.get(f"/api/v1/vehicles/{vehicle.id}/records").json()["total"] == 0


def test_records_hidden_from_other_tenant(client, traccar_mock, vehicle, service_type_id):
    """User B (who cannot see device 1 in Traccar) gets 404 on A's vehicle records."""
    _login(client, traccar_mock, user=USER_B, devices=())

    list_response = client.get(f"/api/v1/vehicles/{vehicle.id}/records")
    create_response = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={"service_type_id": service_type_id, "performed_at": "2026-07-01"},
    )

    assert list_response.status_code == 404
    assert create_response.status_code == 404


def test_record_detail_routes_hidden_from_other_tenant(
    client, db, traccar_mock, vehicle, service_type_id
):
    _login(client, traccar_mock)
    record_id = client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={"service_type_id": service_type_id, "performed_at": "2026-07-01"},
    ).json()["id"]

    from app.api.deps import clear_auth_caches

    clear_auth_caches()
    _login(client, traccar_mock, user=USER_B, devices=())

    assert client.patch(f"/api/v1/records/{record_id}", json={"cost": "1"}).status_code == 404
    assert client.delete(f"/api/v1/records/{record_id}").status_code == 404


def test_vehicles_list_includes_last_service_date(
    client, traccar_mock, vehicle, service_type_id
):
    _login(client, traccar_mock)
    client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={"service_type_id": service_type_id, "performed_at": "2026-05-15"},
    )

    body = client.get("/api/v1/vehicles").json()

    assert body[0]["last_service_date"] == "2026-05-15"


def test_list_all_records_fleet_wide(client, traccar_mock, vehicle, service_type_id):
    _login(client, traccar_mock)
    client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={
            "service_type_id": service_type_id,
            "performed_at": "2026-07-01",
            "performed_by": "Workshop X",
        },
    )

    response = client.get("/api/v1/records")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle_plate"] == "AB-123"
    assert body["items"][0]["vehicle_device_name"] == "Truck"
    assert body["items"][0]["performed_by"] == "Workshop X"


def test_list_all_records_hidden_from_other_tenant(
    client, traccar_mock, vehicle, service_type_id
):
    _login(client, traccar_mock)
    client.post(
        f"/api/v1/vehicles/{vehicle.id}/records",
        json={"service_type_id": service_type_id, "performed_at": "2026-07-01"},
    )

    from app.api.deps import clear_auth_caches

    clear_auth_caches()
    _login(client, traccar_mock, user=USER_B, devices=())

    body = client.get("/api/v1/records").json()
    assert body["total"] == 0
    assert body["items"] == []
