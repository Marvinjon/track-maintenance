"""Traccar event.forward webhook: secret protection and event processing."""

import pytest
from sqlalchemy import select

from app.models import Reminder, ReminderStatus, ServiceType, Vehicle, WebhookEvent

WEBHOOK_URL = "/api/v1/webhooks/traccar"
SECRET = "webhook-test-secret"  # set in conftest env


@pytest.fixture
def setup(db):
    vehicle = Vehicle(traccar_device_id=1)
    service_type = ServiceType(name="Oil change")
    db.add_all([vehicle, service_type])
    db.flush()
    reminder = Reminder(
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        interval_km=15000,
        traccar_maintenance_id=77,
        status=ReminderStatus.ok,
    )
    other_reminder = Reminder(
        vehicle_id=vehicle.id,
        service_type_id=service_type.id,
        interval_days=365,
        status=ReminderStatus.ok,
    )
    db.add_all([reminder, other_reminder])
    db.commit()
    return {"vehicle": vehicle, "reminder": reminder, "other": other_reminder}


def _maintenance_event(device_id=1, maintenance_id=77):
    return {
        "event": {
            "type": "maintenance",
            "deviceId": device_id,
            "maintenanceId": maintenance_id,
        },
        "device": {"id": device_id, "name": "Truck"},
    }


def test_missing_secret_rejected(client):
    assert client.post(WEBHOOK_URL, json={}).status_code == 403


def test_wrong_secret_rejected(client):
    assert client.post(f"{WEBHOOK_URL}?secret=wrong", json={}).status_code == 403
    response = client.post(WEBHOOK_URL, json={}, headers={"X-Webhook-Secret": "wrong"})
    assert response.status_code == 403


def test_valid_secret_via_query_param(client, db):
    response = client.post(f"{WEBHOOK_URL}?secret={SECRET}", json={"event": {"type": "deviceOnline", "deviceId": 5}})
    assert response.status_code == 200

    db.expire_all()
    event = db.execute(select(WebhookEvent)).scalar_one()
    assert event.event_type == "deviceOnline"
    assert event.traccar_device_id == 5
    assert event.payload["event"]["type"] == "deviceOnline"


def test_valid_secret_via_header(client, db):
    response = client.post(
        WEBHOOK_URL, json={"event": {"type": "ignitionOn", "deviceId": 2}},
        headers={"X-Webhook-Secret": SECRET},
    )
    assert response.status_code == 200
    db.expire_all()
    assert db.execute(select(WebhookEvent)).scalar_one().event_type == "ignitionOn"


def test_maintenance_event_sets_matching_reminder_overdue(client, db, setup):
    """The spec's 'maintenance event -> overdue transition' test."""
    response = client.post(
        f"{WEBHOOK_URL}?secret={SECRET}", json=_maintenance_event(maintenance_id=77)
    )

    assert response.status_code == 200
    db.expire_all()
    assert db.get(Reminder, setup["reminder"].id).status == ReminderStatus.overdue
    # Matched by maintenanceId: the unrelated reminder is untouched.
    assert db.get(Reminder, setup["other"].id).status == ReminderStatus.ok


def test_maintenance_event_without_maintenance_id_marks_all(client, db, setup):
    payload = {"event": {"type": "maintenance", "deviceId": 1}}

    assert client.post(f"{WEBHOOK_URL}?secret={SECRET}", json=payload).status_code == 200
    db.expire_all()
    assert db.get(Reminder, setup["reminder"].id).status == ReminderStatus.overdue
    assert db.get(Reminder, setup["other"].id).status == ReminderStatus.overdue


def test_maintenance_event_for_unknown_device_is_stored_quietly(client, db):
    response = client.post(
        f"{WEBHOOK_URL}?secret={SECRET}", json=_maintenance_event(device_id=999)
    )
    assert response.status_code == 200
    db.expire_all()
    assert db.execute(select(WebhookEvent)).scalar_one().traccar_device_id == 999


def test_malformed_payload_still_returns_200(client, db):
    response = client.post(
        f"{WEBHOOK_URL}?secret={SECRET}",
        content=b"not json at all",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    db.expire_all()
    event = db.execute(select(WebhookEvent)).scalar_one()
    assert event.event_type is None
    assert event.payload is None
