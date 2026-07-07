"""Link service types to Traccar maintenance metrics; store Traccar schedule name.

Revision ID: 0009
Revises: 0008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_types",
        sa.Column("traccar_maintenance_type", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_service_types_traccar_maintenance_type",
        "service_types",
        ["traccar_maintenance_type"],
        unique=True,
    )
    op.add_column(
        "reminders",
        sa.Column("traccar_maintenance_name", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reminders", "traccar_maintenance_name")
    op.drop_index("ix_service_types_traccar_maintenance_type", table_name="service_types")
    op.drop_column("service_types", "traccar_maintenance_type")
