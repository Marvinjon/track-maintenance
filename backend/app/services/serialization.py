"""Serialize service types and reminders for API responses."""

from app.models import Reminder, ServiceType
from app.schemas.reminders import ReminderOut
from app.schemas.service_types import ServiceTypeOut


def service_type_to_out(service_type: ServiceType) -> ServiceTypeOut:
    return ServiceTypeOut.model_validate(service_type)


def reminder_to_out(reminder: Reminder, service_type: ServiceType) -> ReminderOut:
    return ReminderOut.model_validate(reminder).model_copy(
        update={
            "service_type_name": service_type.name,
            "traccar_maintenance_type": reminder.traccar_maintenance_type,
        }
    )
