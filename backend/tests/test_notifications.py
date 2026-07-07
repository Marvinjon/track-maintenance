"""Maintenance notification email deduplication and Traccar-scoped recipients."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models import (
    MaintenanceNotification,
    Reminder,
    ReminderStatus,
    ServiceType,
    Vehicle,
)
from app.services.notifications import (
    notify_all_due_reminders,
    notify_reminder,
    resolve_recipients_for_vehicle,
)
from app.services.traccar import NotificationRecipient

from tests.conftest import TRACCAR, USER_A, USER_B, mock_traccar_notification_recipients


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _recipients(*emails: str) -> list[NotificationRecipient]:
    return [
        NotificationRecipient(traccar_user_id=index + 1, email=email)
        for index, email in enumerate(emails)
    ]


@pytest.fixture
def smtp_enabled(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_notify_reminder_sends_email(db, smtp_enabled):
    vehicle = Vehicle(traccar_device_id=1, plate="AB-123")
    service_type = ServiceType(name="Oil change")
    reminder = Reminder(
        vehicle_id=1,
        service_type_id=1,
        interval_km=15000,
        last_service_odometer_km=Decimal("0"),
        status=ReminderStatus.overdue,
    )
    db.add_all([vehicle, service_type])
    db.flush()
    reminder.vehicle_id = vehicle.id
    reminder.service_type_id = service_type.id
    db.add(reminder)
    db.commit()

    with patch("app.services.notifications.send_email") as send_mock:
        sent = notify_reminder(
            db,
            reminder,
            vehicle,
            "Oil change",
            _recipients("a@example.com"),
        )
        db.commit()

    assert sent == 1
    send_mock.assert_called_once()
    logged = db.execute(
        select(MaintenanceNotification).where(
            MaintenanceNotification.reminder_id == reminder.id
        )
    ).scalar_one()
    assert logged.status == ReminderStatus.overdue
    assert logged.recipient_email == "a@example.com"
    assert logged.traccar_user_id == 1


def test_notify_skips_recent_duplicate_per_recipient(db, smtp_enabled):
    vehicle = Vehicle(traccar_device_id=1)
    service_type = ServiceType(name="Oil change")
    reminder = Reminder(
        vehicle_id=1,
        service_type_id=1,
        interval_km=15000,
        status=ReminderStatus.overdue,
    )
    db.add_all([vehicle, service_type])
    db.flush()
    reminder.vehicle_id = vehicle.id
    reminder.service_type_id = service_type.id
    db.add(reminder)
    db.flush()
    db.add(
        MaintenanceNotification(
            reminder_id=reminder.id,
            status=ReminderStatus.overdue,
            channel="email",
            traccar_user_id=1,
            recipient_email="a@example.com",
            sent_at=_utcnow() - timedelta(hours=1),
        )
    )
    db.commit()

    with patch("app.services.notifications.send_email") as send_mock:
        sent = notify_reminder(
            db,
            reminder,
            vehicle,
            "Oil change",
            _recipients("a@example.com", "b@example.com"),
        )

    assert sent == 1
    send_mock.assert_called_once()
    assert send_mock.call_args[0][1] == ["b@example.com"]


def test_notify_all_due_reminders_only_overdue(db, smtp_enabled):
    vehicle = Vehicle(traccar_device_id=1)
    service_type = ServiceType(name="Oil change")
    ok_reminder = Reminder(
        vehicle_id=1,
        service_type_id=1,
        interval_km=15000,
        status=ReminderStatus.ok,
    )
    overdue_reminder = Reminder(
        vehicle_id=1,
        service_type_id=1,
        interval_km=15000,
        status=ReminderStatus.overdue,
    )
    db.add_all([vehicle, service_type])
    db.flush()
    for r in (ok_reminder, overdue_reminder):
        r.vehicle_id = vehicle.id
        r.service_type_id = service_type.id
    db.add_all([ok_reminder, overdue_reminder])
    db.commit()

    async def _resolve(_vehicle):
        return _recipients("a@example.com")

    with (
        patch("app.services.notifications.send_email"),
        patch(
            "app.services.notifications.resolve_recipients_for_vehicle",
            new=AsyncMock(side_effect=_resolve),
        ),
    ):
        sent = __import__("asyncio").run(notify_all_due_reminders(db))

    assert sent == 1


@pytest.mark.asyncio
async def test_resolve_recipients_prefers_maintenance_notification_users(
    traccar_mock,
):
    mock_traccar_notification_recipients(
        traccar_mock,
        device_id=1,
        users=[USER_A, USER_B],
        maintenance_notifications=[
            {"id": 10, "type": "maintenance", "notificators": "web,mail"},
        ],
        notification_user_ids={10: [USER_A["id"]]},
    )
    vehicle = Vehicle(traccar_device_id=1)
    recipients = await resolve_recipients_for_vehicle(vehicle)
    assert len(recipients) == 1
    assert recipients[0].email == USER_A["email"]


@pytest.mark.asyncio
async def test_resolve_recipients_falls_back_to_device_users(traccar_mock):
    mock_traccar_notification_recipients(
        traccar_mock,
        device_id=1,
        users=[USER_A, USER_B],
        device_user_ids=[USER_A["id"]],
    )
    vehicle = Vehicle(traccar_device_id=1)
    recipients = await resolve_recipients_for_vehicle(vehicle)
    assert len(recipients) == 1
    assert recipients[0].email == USER_A["email"]


@pytest.mark.asyncio
async def test_resolve_recipients_tenant_isolation(traccar_mock):
    """Device 1 users must not include users who only have access to device 2."""
    mock_traccar_notification_recipients(
        traccar_mock,
        device_id=1,
        users=[USER_A, USER_B],
        device_user_ids=[USER_A["id"]],
    )
    vehicle = Vehicle(traccar_device_id=1)
    recipients = await resolve_recipients_for_vehicle(vehicle)
    emails = {r.email for r in recipients}
    assert USER_A["email"] in emails
    assert USER_B["email"] not in emails
