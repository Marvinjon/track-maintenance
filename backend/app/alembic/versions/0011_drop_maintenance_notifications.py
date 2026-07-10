"""Drop maintenance_notifications table (email notifications removed).

Revision ID: 0011
Revises: 0010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the table directly — MySQL uses the reminder_id index for the FK,
    # so dropping the index first fails with error 1553.
    op.drop_table("maintenance_notifications")


def downgrade() -> None:
    op.create_table(
        "maintenance_notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("reminder_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("traccar_user_id", sa.BigInteger(), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reminder_id"], ["reminders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maintenance_notifications_reminder_id",
        "maintenance_notifications",
        ["reminder_id"],
    )
