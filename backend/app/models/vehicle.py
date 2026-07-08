from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, SmallInteger, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin


class Vehicle(IdTimestampMixin, Base):
    __tablename__ = "vehicles"

    traccar_device_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    plate: Mapped[str | None] = mapped_column(String(20))
    vin: Mapped[str | None] = mapped_column(String(32))
    make: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(64))
    year: Mapped[int | None] = mapped_column(SmallInteger)
    odometer_km_cached: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    odometer_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    engine_hours_cached: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    notes: Mapped[str | None] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # Manager tenant for catalog rows created via this vehicle (maintenance sync).
    traccar_tenant_user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
