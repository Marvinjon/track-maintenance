"""Manager-scoped isolation for service types and parts."""

from app.models import ServiceType
from tests.conftest import (
    USER_A,
    USER_A_MANAGED,
    USER_B,
    USER_MANAGER,
    USER_OTHER,
    USER_OTHER_MANAGER,
    device,
    mock_devices,
    mock_managed_user,
    mock_session,
)


def _login(client, traccar_mock, user, *, manager_id: int | None = None, devices=(1,)):
    mock_session(traccar_mock, user)
    if manager_id is not None:
        mock_managed_user(traccar_mock, manager_id, user["id"])
    mock_devices(traccar_mock, [device(d) for d in devices])
    client.cookies.set("JSESSIONID", f"user-{user['id']}")


def test_service_types_hidden_across_managers(client, traccar_mock):
    _login(client, traccar_mock, USER_MANAGER, devices=(1,))
    created = client.post(
        "/api/v1/service-types",
        json={"name": "Manager M Service"},
    )
    assert created.status_code == 201
    service_type_id = created.json()["id"]

    _login(client, traccar_mock, USER_OTHER, devices=())
    response = client.get("/api/v1/service-types")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert "Manager M Service" not in names

    patch = client.patch(
        f"/api/v1/service-types/{service_type_id}",
        json={"name": "Hijacked"},
    )
    assert patch.status_code == 404


def test_service_types_shared_within_manager_org(client, traccar_mock):
    _login(client, traccar_mock, USER_MANAGER, devices=(1,))
    created = client.post(
        "/api/v1/service-types",
        json={"name": "Shared Service"},
    )
    assert created.status_code == 201

    _login(client, traccar_mock, USER_A_MANAGED, manager_id=USER_MANAGER["id"], devices=(1,))
    response = client.get("/api/v1/service-types")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert "Shared Service" in names


def test_global_seed_service_types_visible_to_all(client, db, traccar_mock):
    db.add(ServiceType(name="Oil change", default_interval_km=15000))
    db.commit()

    _login(client, traccar_mock, USER_A, devices=())
    names_a = [item["name"] for item in client.get("/api/v1/service-types").json()]
    _login(client, traccar_mock, USER_B, devices=())
    names_b = [item["name"] for item in client.get("/api/v1/service-types").json()]
    assert "Oil change" in names_a
    assert "Oil change" in names_b


def test_parts_hidden_across_managers(client, traccar_mock):
    _login(client, traccar_mock, USER_MANAGER, devices=())
    created = client.post(
        "/api/v1/parts",
        json={"name": "Manager M Filter", "sku": "M-FILTER"},
    )
    assert created.status_code == 201
    part_id = created.json()["id"]

    _login(client, traccar_mock, USER_OTHER_MANAGER, devices=())
    response = client.get("/api/v1/parts")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert "Manager M Filter" not in names

    patch = client.patch(f"/api/v1/parts/{part_id}", json={"name": "Hijacked"})
    assert patch.status_code == 404


def test_parts_shared_within_manager_org(client, traccar_mock):
    _login(client, traccar_mock, USER_MANAGER, devices=())
    created = client.post(
        "/api/v1/parts",
        json={"name": "Shared Filter", "sku": "SHARED-1"},
    )
    assert created.status_code == 201

    _login(client, traccar_mock, USER_A_MANAGED, manager_id=USER_MANAGER["id"], devices=())
    response = client.get("/api/v1/parts")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert "Shared Filter" in names


def test_standalone_users_have_separate_service_type_tenants(client, traccar_mock):
    _login(client, traccar_mock, USER_A, devices=())
    assert client.post(
        "/api/v1/service-types",
        json={"name": "Tenant A Service"},
    ).status_code == 201

    _login(client, traccar_mock, USER_B, devices=())
    names = [item["name"] for item in client.get("/api/v1/service-types").json()]
    assert "Tenant A Service" not in names
