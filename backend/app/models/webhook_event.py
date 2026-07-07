from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin


class WebhookEvent(IdTimestampMixin, Base):
    __tablename__ = "webhook_events"

    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(64))
    traccar_device_id: Mapped[int | None] = mapped_column(BigInteger)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
