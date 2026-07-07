from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntPK, IdTimestampMixin
from app.models.reminder import ReminderStatus


class MaintenanceNotification(IdTimestampMixin, Base):
    __tablename__ = "maintenance_notifications"

    reminder_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("reminders.id"), nullable=False, index=True
    )
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(
            ReminderStatus,
            values_callable=lambda e: [m.value for m in e],
            name="reminder_status",
        ),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    traccar_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
