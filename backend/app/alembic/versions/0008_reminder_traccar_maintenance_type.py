"""Store Traccar maintenance metric type on linked reminders.

Revision ID: 0008
Revises: 0007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reminders",
        sa.Column("traccar_maintenance_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reminders", "traccar_maintenance_type")
