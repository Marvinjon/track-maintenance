from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdTimestampMixin


class ServiceType(IdTimestampMixin, Base):
    __tablename__ = "service_types"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Traccar maintenance metric key (e.g. obdOdometer); null for local-only types.
    traccar_maintenance_type: Mapped[str | None] = mapped_column(String(50), unique=True)
    default_interval_km: Mapped[int | None] = mapped_column(Integer)
    default_interval_days: Mapped[int | None] = mapped_column(Integer)
