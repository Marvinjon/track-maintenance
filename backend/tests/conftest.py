import os

# Must be set before any app import: get_settings() is lru_cached.
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["TRACCAR_URL"] = "http://traccar.test"
os.environ["TRACCAR_PUBLIC_URL"] = ""
os.environ["TRACCAR_ADMIN_TOKEN"] = "admin-test-token"
os.environ["WEBHOOK_SECRET"] = "webhook-test-secret"

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import clear_auth_caches
from app.db import get_db
from app.main import app
from app.models import Base
from app.services.user_sync import clear_user_sync_throttle

import app.db as db_module

TRACCAR = "http://traccar.test"

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_foreign_keys(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clean_state():
    Base.metadata.create_all(engine)
    clear_auth_caches()
    clear_user_sync_throttle()
    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = TestingSessionLocal
    try:
        yield
    finally:
        db_module.SessionLocal = original_session_local
        Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def traccar_mock():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=rf"{TRACCAR}/api/maintenances.*").mock(
            return_value=Response(200, json=[])
        )
        mock.get(url__regex=rf"{TRACCAR}/api/maintenance.*").mock(
            return_value=Response(200, json=[])
        )
        mock.get(f"{TRACCAR}/api/permissions").mock(return_value=Response(200, json=[]))
        yield mock


USER_A = {"id": 1, "name": "User A", "email": "a@example.com", "administrator": False, "userLimit": 0}
USER_B = {"id": 2, "name": "User B", "email": "b@example.com", "administrator": False, "userLimit": 0}
USER_MANAGER = {"id": 10, "name": "Manager M", "email": "m@example.com", "administrator": False, "userLimit": 10}
USER_A_MANAGED = {"id": 11, "name": "User A2", "email": "a2@example.com", "administrator": False, "userLimit": 0}
USER_OTHER_MANAGER = {"id": 20, "name": "Manager N", "email": "n@example.com", "administrator": False, "userLimit": 10}
USER_READONLY = {
    "id": 3,
    "name": "Read Only",
    "email": "readonly@example.com",
    "administrator": False,
    "userLimit": 0,
    "readonly": True,
    "deviceReadonly": False,
}


def mock_managed_user(mock: respx.MockRouter, manager_id: int, user_id: int):
    """Mock Traccar permission link: manager manages user."""

    def permissions_responder(request):
        params = request.url.params
        if (
            params.get("managedUserId") == str(user_id)
            and params.get("userId") == "0"
        ):
            return Response(
                200,
                json=[{"userId": manager_id, "managedUserId": user_id}],
            )
        return Response(200, json=[])

    return mock.get(f"{TRACCAR}/api/permissions").mock(side_effect=permissions_responder)


def mock_session(mock: respx.MockRouter, user: dict | None, status: int = 200):
    """Mock GET /api/session. user=None means Traccar rejects the credential."""
    if user is None:
        return mock.get(f"{TRACCAR}/api/session").mock(return_value=Response(401))
    return mock.get(f"{TRACCAR}/api/session").mock(return_value=Response(status, json=user))


def mock_devices(mock: respx.MockRouter, devices: list[dict]):
    """Mock GET /api/devices (both the full list and ?id= lookups)."""

    def responder(request):
        device_id = request.url.params.get("id")
        if device_id is not None:
            matching = [d for d in devices if d["id"] == int(device_id)]
            return Response(200, json=matching)
        return Response(200, json=devices)

    return mock.get(f"{TRACCAR}/api/devices").mock(side_effect=responder)


def device(device_id: int, name: str = "Truck") -> dict:
    return {"id": device_id, "name": name, "uniqueId": f"unique-{device_id}", "status": "online"}


def mock_positions(mock: respx.MockRouter, positions_by_device: dict[int, list[dict]]):
    """Mock GET /api/positions?deviceId=."""

    def responder(request):
        device_id = int(request.url.params["deviceId"])
        return Response(200, json=positions_by_device.get(device_id, []))

    return mock.get(f"{TRACCAR}/api/positions").mock(side_effect=responder)


def position(device_id: int, **attributes) -> dict:
    return {"deviceId": device_id, "attributes": attributes}


def mock_accumulators_update(mock: respx.MockRouter):
    """Mock PUT /api/devices/{id}/accumulators (admin token)."""
    return mock.put(url__regex=rf"{TRACCAR}/api/devices/\d+/accumulators").mock(
        return_value=Response(204)
    )


def mock_traccar_notification_recipients(
    mock: respx.MockRouter,
    *,
    device_id: int,
    users: list[dict],
    device_user_ids: list[int] | None = None,
    maintenance_notifications: list[dict] | None = None,
    notification_user_ids: dict[int, list[int]] | None = None,
) -> None:
    """Wire admin Traccar API mocks for maintenance email recipient lookup."""

    def users_responder(request):
        if request.url.params.get("all") == "true":
            return Response(200, json=users)
        return Response(200, json=users)

    def notifications_responder(request):
        if request.url.params.get("all") == "true":
            return Response(200, json=maintenance_notifications or [])
        return Response(200, json=maintenance_notifications or [])

    def permissions_responder(request):
        params = request.url.params
        linked_device_id = params.get("deviceId")
        notification_id = params.get("notificationId")
        user_id = params.get("userId")

        if linked_device_id == str(device_id) and notification_id == "0":
            if maintenance_notifications:
                return Response(
                    200,
                    json=[
                        {"deviceId": device_id, "notificationId": item["id"]}
                        for item in maintenance_notifications
                    ],
                )
            return Response(200, json=[])

        if user_id == "0" and notification_id not in (None, "0"):
            linked_users = (notification_user_ids or {}).get(int(notification_id), [])
            return Response(
                200,
                json=[
                    {"userId": uid, "notificationId": int(notification_id)}
                    for uid in linked_users
                ],
            )

        if linked_device_id == str(device_id) and user_id == "0":
            linked_users = device_user_ids if device_user_ids is not None else [
                user["id"] for user in users
            ]
            return Response(
                200,
                json=[{"userId": uid, "deviceId": device_id} for uid in linked_users],
            )

        return Response(200, json=[])

    mock.get(f"{TRACCAR}/api/users").mock(side_effect=users_responder)
    mock.get(f"{TRACCAR}/api/notifications").mock(side_effect=notifications_responder)
    mock.get(f"{TRACCAR}/api/permissions").mock(side_effect=permissions_responder)
