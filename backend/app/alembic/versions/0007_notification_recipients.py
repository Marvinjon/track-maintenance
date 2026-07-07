"""Per-recipient maintenance notification deduplication.

Revision ID: 0007
Revises: 0006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "maintenance_notifications",
        sa.Column("traccar_user_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "maintenance_notifications",
        sa.Column("recipient_email", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("maintenance_notifications", "recipient_email", server_default=None)


def downgrade() -> None:
    op.drop_column("maintenance_notifications", "recipient_email")
    op.drop_column("maintenance_notifications", "traccar_user_id")
