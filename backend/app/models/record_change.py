from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntPK, IdTimestampMixin


class RecordChange(IdTimestampMixin, Base):
    __tablename__ = "record_changes"

    maintenance_record_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("maintenance_records.id"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_by_traccar_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
