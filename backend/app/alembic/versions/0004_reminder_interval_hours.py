"""Add interval_hours and last_service_engine_hours to reminders.

Revision ID: 0004
Revises: 0003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reminders", sa.Column("interval_hours", sa.Integer(), nullable=True))
    op.add_column(
        "reminders",
        sa.Column("last_service_engine_hours", sa.Numeric(12, 1), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reminders", "last_service_engine_hours")
    op.drop_column("reminders", "interval_hours")
