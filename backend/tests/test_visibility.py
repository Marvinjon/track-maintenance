"""Multi-tenancy: vehicle visibility is exactly Traccar device visibility."""

import pytest
from fastapi import HTTPException

from app.api.deps import AuthContext, TraccarUser, verify_device_access
from app.models import Vehicle
from app.services.traccar import TraccarService, UserCredential
from tests.conftest import TRACCAR, USER_A, USER_B, device, mock_devices, mock_session


def test_vehicles_list_only_contains_users_own_devices(client, db, traccar_mock):
    """User A sees devices 1 and 2. A local vehicle row exists for device 3
    (another tenant's) — it must NOT appear in A's list."""
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1), device(2)])

    db.add(Vehicle(traccar_device_id=1, plate="AB-123"))
    db.add(Vehicle(traccar_device_id=3, plate="ZZ-999"))  # not visible to user A
    db.commit()

    client.cookies.set("JSESSIONID", "user-a")
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 200
    body = response.json()
    returned_ids = {v["traccar_device_id"] for v in body}
    assert returned_ids == {1, 2}
    plates = {v["plate"] for v in body}
    assert "ZZ-999" not in plates


def test_unregistered_devices_are_returned_as_stubs(client, db, traccar_mock):
    mock_session(traccar_mock, USER_A)
    mock_devices(traccar_mock, [device(1), device(2)])

    db.add(Vehicle(traccar_device_id=1, plate="AB-123", make="Toyota"))
    db.commit()

    client.cookies.set("JSESSIONID", "user-a")
    response = client.get("/api/v1/vehicles")

    body = {v["traccar_device_id"]: v for v in response.json()}
    assert body[1]["registered"] is True
    assert body[1]["plate"] == "AB-123"
    assert body[2]["registered"] is False
    assert body[2]["id"] is None
    assert body[2]["device_name"] == "Truck"


def _ctx(user: dict, tenant_user_id: int | None = None) -> AuthContext:
    uid = user["id"]
    if tenant_user_id is None:
        tenant_user_id = uid if not user.get("administrator") else None
    return AuthContext(
        user=TraccarUser(
            id=uid,
            name=user["name"],
            email=user["email"],
            administrator=user["administrator"],
            user_limit=int(user.get("userLimit", 0)),
            readonly=bool(user.get("readonly", False)),
            device_readonly=bool(user.get("deviceReadonly", False)),
        ),
        credential=UserCredential(session_cookie=f"cookie-{uid}"),
        tenant_user_id=tenant_user_id,
    )


def _service() -> TraccarService:
    return TraccarService(TRACCAR)


async def test_device_access_denied_when_traccar_hides_device(traccar_mock):
    """Traccar returns no device for user B's credential -> 404, existence not revealed."""
    mock_devices(traccar_mock, [])  # user sees nothing

    with pytest.raises(HTTPException) as exc_info:
        await verify_device_access(_ctx(USER_B), _service(), traccar_device_id=1)

    assert exc_info.value.status_code == 404


async def test_device_access_granted_when_traccar_returns_device(traccar_mock):
    mock_devices(traccar_mock, [device(1)])

    # Must not raise.
    await verify_device_access(_ctx(USER_A), _service(), traccar_device_id=1)


async def test_device_access_is_cached_per_user_and_device(traccar_mock):
    devices_route = mock_devices(traccar_mock, [device(1)])

    await verify_device_access(_ctx(USER_A), _service(), traccar_device_id=1)
    await verify_device_access(_ctx(USER_A), _service(), traccar_device_id=1)

    assert devices_route.call_count == 1

    # A different user must trigger a fresh check (no cross-user cache hits).
    await verify_device_access(_ctx(USER_B), _service(), traccar_device_id=1)
    assert devices_route.call_count == 2


async def test_denied_access_is_not_cached(traccar_mock):
    devices_route = mock_devices(traccar_mock, [])

    for _ in range(2):
        with pytest.raises(HTTPException):
            await verify_device_access(_ctx(USER_B), _service(), traccar_device_id=1)

    # Denials must be re-checked, never cached.
    assert devices_route.call_count == 2
