import enum
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Numeric, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntPK, IdTimestampMixin


class StockMovementReason(str, enum.Enum):
    purchase = "purchase"
    used_in_service = "used_in_service"
    adjustment = "adjustment"
    return_ = "return"


class Part(IdTimestampMixin, Base):
    __tablename__ = "parts"
    __table_args__ = (
        UniqueConstraint("traccar_tenant_user_id", "sku", name="uq_parts_tenant_sku"),
    )

    sku: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pcs", server_default="pcs"
    )
    min_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # Manager tenant owner; NULL = global catalog row visible to every tenant.
    traccar_tenant_user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)


class StockMovement(IdTimestampMixin, Base):
    __tablename__ = "stock_movements"

    part_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("parts.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[StockMovementReason] = mapped_column(
        Enum(
            StockMovementReason,
            values_callable=lambda e: [m.value for m in e],
            name="stock_movement_reason",
        ),
        nullable=False,
    )
    maintenance_record_id: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("maintenance_records.id")
    )
    note: Mapped[str | None] = mapped_column(String(255))
    created_by_traccar_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
