"""Allow multiple vehicle rows per tracker over time (one active).

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_vehicles_traccar_device_id", "vehicles", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_vehicles_traccar_device_id", "vehicles", ["traccar_device_id"]
    )
