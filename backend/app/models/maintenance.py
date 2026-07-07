from datetime import date
from decimal import Decimal

from sqlalchemy import CHAR, BigInteger, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntPK, IdTimestampMixin


class MaintenanceRecord(IdTimestampMixin, Base):
    __tablename__ = "maintenance_records"

    vehicle_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("vehicles.id"), nullable=False, index=True
    )
    service_type_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("service_types.id"), nullable=False
    )
    performed_at: Mapped[date] = mapped_column(Date, nullable=False)
    odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 1))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, default="ISK", server_default="ISK"
    )
    performed_by: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_traccar_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class RecordPart(IdTimestampMixin, Base):
    __tablename__ = "record_parts"

    maintenance_record_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("maintenance_records.id"), nullable=False, index=True
    )
    part_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("parts.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
