"""Add manager tenant scope to catalog tables and vehicles.

Revision ID: 0010
Revises: 0009
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "service_types",
        sa.Column("traccar_tenant_user_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_service_types_traccar_tenant_user_id",
        "service_types",
        ["traccar_tenant_user_id"],
    )
    op.drop_index("ix_service_types_traccar_maintenance_type", table_name="service_types")
    op.create_unique_constraint(
        "uq_service_types_tenant_traccar_type",
        "service_types",
        ["traccar_tenant_user_id", "traccar_maintenance_type"],
    )

    op.add_column(
        "parts",
        sa.Column("traccar_tenant_user_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_parts_traccar_tenant_user_id",
        "parts",
        ["traccar_tenant_user_id"],
    )
    op.drop_constraint("sku", "parts", type_="unique")
    op.create_unique_constraint(
        "uq_parts_tenant_sku",
        "parts",
        ["traccar_tenant_user_id", "sku"],
    )

    op.add_column(
        "vehicles",
        sa.Column("traccar_tenant_user_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_vehicles_traccar_tenant_user_id",
        "vehicles",
        ["traccar_tenant_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_vehicles_traccar_tenant_user_id", table_name="vehicles")
    op.drop_column("vehicles", "traccar_tenant_user_id")

    op.drop_constraint("uq_parts_tenant_sku", "parts", type_="unique")
    op.create_unique_constraint("sku", "parts", ["sku"])
    op.drop_index("ix_parts_traccar_tenant_user_id", table_name="parts")
    op.drop_column("parts", "traccar_tenant_user_id")

    op.drop_constraint("uq_service_types_tenant_traccar_type", "service_types", type_="unique")
    op.create_index(
        "ix_service_types_traccar_maintenance_type",
        "service_types",
        ["traccar_maintenance_type"],
        unique=True,
    )
    op.drop_index("ix_service_types_traccar_tenant_user_id", table_name="service_types")
    op.drop_column("service_types", "traccar_tenant_user_id")
