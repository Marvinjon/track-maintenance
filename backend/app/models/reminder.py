import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntPK, IdTimestampMixin


class ReminderStatus(str, enum.Enum):
    ok = "ok"
    due_soon = "due_soon"
    overdue = "overdue"


class Reminder(IdTimestampMixin, Base):
    __tablename__ = "reminders"

    vehicle_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("vehicles.id"), nullable=False, index=True
    )
    service_type_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("service_types.id"), nullable=False
    )
    traccar_maintenance_id: Mapped[int | None] = mapped_column(BigInteger)
    # Traccar metric key (e.g. totalDistance, obdOdometer, hours) for service-reset push.
    traccar_maintenance_type: Mapped[str | None] = mapped_column(String(50))
    # User-defined label for this schedule in Traccar (e.g. "Oil change").
    traccar_maintenance_name: Mapped[str | None] = mapped_column(String(100))
    interval_km: Mapped[int | None] = mapped_column(Integer)
    interval_days: Mapped[int | None] = mapped_column(Integer)
    interval_hours: Mapped[int | None] = mapped_column(Integer)
    last_service_odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    last_service_engine_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    last_service_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(
            ReminderStatus,
            values_callable=lambda e: [m.value for m in e],
            name="reminder_status",
        ),
        nullable=False,
        default=ReminderStatus.ok,
        server_default="ok",
    )
    # True when the Traccar maintenance mirror could not be created/updated;
    # the reminder still works locally.
    sync_error: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
