"""Service type CRUD and per-type maintenance history."""

import pytest
from sqlalchemy import select

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


def test_delete_unused_service_type(client, setup, traccar_mock):
    created = client.post(
        "/api/v1/service-types",
        json={"name": "Coolant flush"},
    )
    assert created.status_code == 201
    service_type_id = created.json()["id"]

    response = client.delete(f"/api/v1/service-types/{service_type_id}")
    assert response.status_code == 204
    assert all(
        item["id"] != service_type_id
        for item in client.get("/api/v1/service-types").json()
    )


def test_delete_service_type_in_use_409(client, setup, traccar_mock):
    created = client.post(
        "/api/v1/service-types",
        json={"name": "Tire rotation"},
    )
    assert created.status_code == 201
    service_type_id = created.json()["id"]
    client.post(
        f"/api/v1/vehicles/{setup['vehicle'].id}/records",
        json={
            "service_type_id": service_type_id,
            "performed_at": "2026-07-01",
        },
    )

    response = client.delete(f"/api/v1/service-types/{service_type_id}")
    assert response.status_code == 409


def test_delete_service_type_readonly_forbidden(client, setup, traccar_mock):
    from tests.conftest import USER_READONLY, mock_session

    created = client.post(
        "/api/v1/service-types",
        json={"name": "Brake inspection"},
    )
    service_type_id = created.json()["id"]

    mock_session(traccar_mock, USER_READONLY)
    client.cookies.set("JSESSIONID", "user-readonly")
    response = client.delete(f"/api/v1/service-types/{service_type_id}")
    assert response.status_code == 403


def test_delete_global_service_type_forbidden_for_tenant_user(client, db, traccar_mock):
    from tests.conftest import USER_A, mock_devices, mock_session

    db.add(ServiceType(name="Oil change", default_interval_km=15000))
    db.commit()
    service_type_id = db.execute(
        select(ServiceType).where(ServiceType.name == "Oil change")
    ).scalar_one().id

    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [])
    client.cookies.set("JSESSIONID", "user-a")
    response = client.delete(f"/api/v1/service-types/{service_type_id}")
    assert response.status_code == 403
