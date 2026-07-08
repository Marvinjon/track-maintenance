from sqlalchemy import BigInteger, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin


class ServiceType(IdTimestampMixin, Base):
    __tablename__ = "service_types"
    __table_args__ = (
        UniqueConstraint(
            "traccar_tenant_user_id",
            "traccar_maintenance_type",
            name="uq_service_types_tenant_traccar_type",
        ),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Traccar maintenance metric key (e.g. obdOdometer); null for local-only types.
    traccar_maintenance_type: Mapped[str | None] = mapped_column(String(50))
    default_interval_km: Mapped[int | None] = mapped_column(Integer)
    default_interval_days: Mapped[int | None] = mapped_column(Integer)
    # Manager tenant owner; NULL = global defaults visible to every tenant.
    traccar_tenant_user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
