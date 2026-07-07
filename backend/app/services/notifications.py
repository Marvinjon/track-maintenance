"""Email notifications for due/overdue maintenance reminders.

Recipients are resolved per vehicle from Traccar: users linked to maintenance
notifications (mail channel) for that device, or — if none are configured —
users with direct device access. This mirrors Traccar tenant isolation so
company Y never receives alerts for company X's vehicles.
"""

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import MaintenanceNotification, Reminder, ReminderStatus, ServiceType, Vehicle
from app.services.traccar import NotificationRecipient, TraccarUnavailable, get_traccar

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _was_notified_recently(
    db: Session,
    reminder_id: int,
    status: ReminderStatus,
    recipient_email: str,
    cooldown_hours: int,
) -> bool:
    cutoff = _utcnow_naive() - timedelta(hours=cooldown_hours)
    existing = db.execute(
        select(MaintenanceNotification.id)
        .where(
            MaintenanceNotification.reminder_id == reminder_id,
            MaintenanceNotification.status == status,
            MaintenanceNotification.recipient_email == recipient_email,
            MaintenanceNotification.sent_at >= cutoff,
        )
        .limit(1)
    ).scalar_one_or_none()
    return existing is not None


def _build_email(
    *,
    vehicle: Vehicle,
    service_type_name: str,
    status: ReminderStatus,
    device_name: str | None,
) -> EmailMessage:
    settings = get_settings()
    label = vehicle.plate or device_name or f"Device {vehicle.traccar_device_id}"
    status_label = status.value.replace("_", " ")
    subject = f"Maintenance {status_label}: {service_type_name} ({label})"
    body = (
        f"Vehicle: {label}\n"
        f"Service: {service_type_name}\n"
        f"Status: {status_label}\n"
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg.set_content(body)
    return msg


def send_email(msg: EmailMessage, recipients: list[str]) -> None:
    settings = get_settings()
    msg["To"] = ", ".join(recipients)
    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)


async def resolve_recipients_for_vehicle(vehicle: Vehicle) -> list[NotificationRecipient]:
    """Look up Traccar users who should be emailed for this vehicle."""
    try:
        return await get_traccar().as_admin().list_maintenance_email_recipients(
            vehicle.traccar_device_id
        )
    except TraccarUnavailable:
        logger.warning(
            "Could not resolve notification recipients for device %s",
            vehicle.traccar_device_id,
        )
        return []


def notify_reminder(
    db: Session,
    reminder: Reminder,
    vehicle: Vehicle,
    service_type_name: str,
    recipients: list[NotificationRecipient],
    *,
    device_name: str | None = None,
    force: bool = False,
) -> int:
    """Email eligible Traccar users. Returns count sent."""
    settings = get_settings()
    if not settings.smtp_configured:
        return 0
    if reminder.status not in (ReminderStatus.due_soon, ReminderStatus.overdue):
        return 0
    if not recipients:
        return 0

    sent = 0
    for recipient in recipients:
        if not force and _was_notified_recently(
            db,
            reminder.id,
            reminder.status,
            recipient.email,
            settings.notification_cooldown_hours,
        ):
            continue

        try:
            msg = _build_email(
                vehicle=vehicle,
                service_type_name=service_type_name,
                status=reminder.status,
                device_name=device_name,
            )
            send_email(msg, [recipient.email])
        except Exception:
            logger.exception(
                "Failed to send maintenance notification for reminder %s to %s",
                reminder.id,
                recipient.email,
            )
            continue

        db.add(
            MaintenanceNotification(
                reminder_id=reminder.id,
                status=reminder.status,
                channel="email",
                traccar_user_id=recipient.traccar_user_id,
                recipient_email=recipient.email,
                sent_at=_utcnow_naive(),
            )
        )
        sent += 1
    return sent


async def notify_reminders_for_vehicle(
    db: Session,
    vehicle: Vehicle,
    *,
    device_name: str | None = None,
    reminder_ids: list[int] | None = None,
    force: bool = False,
) -> int:
    """Notify on due reminders for one vehicle. Returns count sent."""
    recipients = await resolve_recipients_for_vehicle(vehicle)
    if not recipients:
        return 0

    query = (
        select(Reminder, ServiceType.name)
        .join(ServiceType, Reminder.service_type_id == ServiceType.id)
        .where(Reminder.vehicle_id == vehicle.id)
    )
    if reminder_ids is not None:
        query = query.where(Reminder.id.in_(reminder_ids))

    sent = 0
    for reminder, service_type_name in db.execute(query).all():
        sent += notify_reminder(
            db,
            reminder,
            vehicle,
            service_type_name,
            recipients,
            device_name=device_name,
            force=force,
        )
    return sent


async def notify_all_due_reminders(db: Session) -> int:
    """Scan active vehicles and email due reminders. Returns count sent."""
    vehicles = (
        db.execute(select(Vehicle).where(Vehicle.archived.is_(False))).scalars().all()
    )
    sent = 0
    for vehicle in vehicles:
        sent += await notify_reminders_for_vehicle(db, vehicle)
    if sent:
        db.commit()
    return sent


async def run_scheduled_notifications() -> None:
    """Entry point for the APScheduler job (owns its DB session)."""
    from app.db import SessionLocal

    if not get_settings().smtp_configured:
        return

    db = SessionLocal()
    try:
        sent = await notify_all_due_reminders(db)
        if sent:
            logger.info("Maintenance notification job sent %d emails", sent)
    except Exception:
        logger.exception("Scheduled maintenance notification job failed")
    finally:
        db.close()
