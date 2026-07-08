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


def _column_names(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _index_names(table: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}


def _unique_constraint_names(table: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table)
    }


def _drop_parts_sku_unique() -> None:
    """Drop the legacy single-column SKU unique key (name differs by install path)."""
    for name in ("uq_parts_sku", "sku"):
        if name in _unique_constraint_names("parts"):
            op.drop_constraint(name, "parts", type_="unique")
            return

    for index in sa.inspect(op.get_bind()).get_indexes("parts"):
        if index.get("unique") and index["column_names"] == ["sku"]:
            op.drop_index(index["name"], table_name="parts")
            return


def upgrade() -> None:
    if "traccar_tenant_user_id" not in _column_names("service_types"):
        op.add_column(
            "service_types",
            sa.Column("traccar_tenant_user_id", sa.BigInteger(), nullable=True),
        )
    if "ix_service_types_traccar_tenant_user_id" not in _index_names("service_types"):
        op.create_index(
            "ix_service_types_traccar_tenant_user_id",
            "service_types",
            ["traccar_tenant_user_id"],
        )
    if "ix_service_types_traccar_maintenance_type" in _index_names("service_types"):
        op.drop_index("ix_service_types_traccar_maintenance_type", table_name="service_types")
    if "uq_service_types_tenant_traccar_type" not in _unique_constraint_names(
        "service_types"
    ):
        op.create_unique_constraint(
            "uq_service_types_tenant_traccar_type",
            "service_types",
            ["traccar_tenant_user_id", "traccar_maintenance_type"],
        )

    if "traccar_tenant_user_id" not in _column_names("parts"):
        op.add_column(
            "parts",
            sa.Column("traccar_tenant_user_id", sa.BigInteger(), nullable=True),
        )
    if "ix_parts_traccar_tenant_user_id" not in _index_names("parts"):
        op.create_index(
            "ix_parts_traccar_tenant_user_id",
            "parts",
            ["traccar_tenant_user_id"],
        )
    if "uq_parts_tenant_sku" not in _unique_constraint_names("parts"):
        _drop_parts_sku_unique()
        op.create_unique_constraint(
            "uq_parts_tenant_sku",
            "parts",
            ["traccar_tenant_user_id", "sku"],
        )

    if "traccar_tenant_user_id" not in _column_names("vehicles"):
        op.add_column(
            "vehicles",
            sa.Column("traccar_tenant_user_id", sa.BigInteger(), nullable=True),
        )
    if "ix_vehicles_traccar_tenant_user_id" not in _index_names("vehicles"):
        op.create_index(
            "ix_vehicles_traccar_tenant_user_id",
            "vehicles",
            ["traccar_tenant_user_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_vehicles_traccar_tenant_user_id", table_name="vehicles")
    op.drop_column("vehicles", "traccar_tenant_user_id")

    op.drop_constraint("uq_parts_tenant_sku", "parts", type_="unique")
    op.create_unique_constraint("uq_parts_sku", "parts", ["sku"])
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
