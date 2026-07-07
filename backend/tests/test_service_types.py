"""Service type CRUD and per-type maintenance history."""

import pytest

from app.models import ServiceType, Vehicle
from tests.conftest import USER_A, device, mock_devices, mock_session


@pytest.fixture
def setup(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1)])
    client.cookies.set("JSESSIONID", "user-a")

    vehicle = Vehicle(traccar_device_id=1, plate="AB-123")
    service_type = ServiceType(name="Oil change", default_interval_km=15000)
    db.add_all([vehicle, service_type])
    db.commit()
    return {"vehicle": vehicle, "service_type": service_type}


def test_create_service_type(client, setup, traccar_mock):
    response = client.post(
        "/api/v1/service-types",
        json={"name": "Transmission fluid", "default_interval_km": 60000},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Transmission fluid"
    assert body["default_interval_km"] == 60000


def test_create_service_type_duplicate_name_409(client, setup, traccar_mock):
    response = client.post(
        "/api/v1/service-types",
        json={"name": "Oil change"},
    )
    assert response.status_code == 409


def test_update_service_type(client, setup, traccar_mock):
    response = client.patch(
        f"/api/v1/service-types/{setup['service_type'].id}",
        json={"name": "Engine oil", "default_interval_days": 365},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Engine oil"
    assert body["default_interval_days"] == 365


def test_list_records_for_service_type(client, setup, traccar_mock):
    client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "performed_by": "Workshop A",
        },
    )

    response = client.get(
        f"/api/v1/service-types/{setup['service_type'].id}/records"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle_plate"] == "AB-123"
    assert body["items"][0]["performed_by"] == "Workshop A"


def test_get_record(client, setup, traccar_mock):
    record_id = client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": setup["service_type"].id,
            "performed_at": "2026-07-01",
            "notes": "Synthetic oil",
        },
    ).json()["id"]

    response = client.get(f"/api/v1/records/{record_id}")
    assert response.status_code == 200
    assert response.json()["notes"] == "Synthetic oil"
    assert response.json()["changes"] == []
