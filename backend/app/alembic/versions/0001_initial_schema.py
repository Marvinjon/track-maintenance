"""Initial schema: vehicles, service_types, maintenance_records, parts,
stock_movements, record_parts, reminders, webhook_events + service type seeds.

Revision ID: 0001
Revises:
Create Date: 2026-07-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SQLite (used in dev/test smoke runs) only autoincrements INTEGER primary
# keys; MySQL (production) gets BIGINT AUTO_INCREMENT.
_BigIntPK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", _BigIntPK, autoincrement=True, primary_key=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "vehicles",
        *_common_columns(),
        sa.Column("traccar_device_id", sa.BigInteger(), nullable=False),
        sa.Column("plate", sa.String(20), nullable=True),
        sa.Column("vin", sa.String(32), nullable=True),
        sa.Column("make", sa.String(64), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("odometer_km_cached", sa.Numeric(12, 1), nullable=True),
        sa.Column("odometer_synced_at", sa.DateTime(), nullable=True),
        sa.Column("engine_hours_cached", sa.Numeric(12, 1), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("traccar_device_id", name="uq_vehicles_traccar_device_id"),
    )
    op.create_index("ix_vehicles_traccar_device_id", "vehicles", ["traccar_device_id"])

    op.create_table(
        "service_types",
        *_common_columns(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("default_interval_km", sa.Integer(), nullable=True),
        sa.Column("default_interval_days", sa.Integer(), nullable=True),
    )

    op.create_table(
        "maintenance_records",
        *_common_columns(),
        sa.Column(
            "vehicle_id", sa.BigInteger(), sa.ForeignKey("vehicles.id"), nullable=False
        ),
        sa.Column(
            "service_type_id",
            sa.BigInteger(),
            sa.ForeignKey("service_types.id"),
            nullable=False,
        ),
        sa.Column("performed_at", sa.Date(), nullable=False),
        sa.Column("odometer_km", sa.Numeric(12, 1), nullable=True),
        sa.Column("cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="ISK"),
        sa.Column("performed_by", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_traccar_user_id", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_maintenance_records_vehicle_id", "maintenance_records", ["vehicle_id"])

    op.create_table(
        "parts",
        *_common_columns(),
        sa.Column("sku", sa.String(64), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="pcs"),
        sa.Column("min_stock", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("sku", name="uq_parts_sku"),
    )

    op.create_table(
        "stock_movements",
        *_common_columns(),
        sa.Column("part_id", sa.BigInteger(), sa.ForeignKey("parts.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "purchase",
                "used_in_service",
                "adjustment",
                "return",
                name="stock_movement_reason",
            ),
            nullable=False,
        ),
        sa.Column(
            "maintenance_record_id",
            sa.BigInteger(),
            sa.ForeignKey("maintenance_records.id"),
            nullable=True,
        ),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_by_traccar_user_id", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_stock_movements_part_id", "stock_movements", ["part_id"])

    op.create_table(
        "record_parts",
        *_common_columns(),
        sa.Column(
            "maintenance_record_id",
            sa.BigInteger(),
            sa.ForeignKey("maintenance_records.id"),
            nullable=False,
        ),
        sa.Column("part_id", sa.BigInteger(), sa.ForeignKey("parts.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
    )
    op.create_index(
        "ix_record_parts_maintenance_record_id", "record_parts", ["maintenance_record_id"]
    )

    op.create_table(
        "reminders",
        *_common_columns(),
        sa.Column(
            "vehicle_id", sa.BigInteger(), sa.ForeignKey("vehicles.id"), nullable=False
        ),
        sa.Column(
            "service_type_id",
            sa.BigInteger(),
            sa.ForeignKey("service_types.id"),
            nullable=False,
        ),
        sa.Column("traccar_maintenance_id", sa.BigInteger(), nullable=True),
        sa.Column("interval_km", sa.Integer(), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column("last_service_odometer_km", sa.Numeric(12, 1), nullable=True),
        sa.Column("last_service_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ok", "due_soon", "overdue", name="reminder_status"),
            nullable=False,
            server_default="ok",
        ),
    )
    op.create_index("ix_reminders_vehicle_id", "reminders", ["vehicle_id"])

    op.create_table(
        "webhook_events",
        *_common_columns(),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=True),
        sa.Column("traccar_device_id", sa.BigInteger(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
    )

    service_types = sa.table(
        "service_types",
        sa.column("name", sa.String),
        sa.column("default_interval_km", sa.Integer),
        sa.column("default_interval_days", sa.Integer),
    )
    op.bulk_insert(
        service_types,
        [
            {"name": "Oil change", "default_interval_km": 15000, "default_interval_days": 365},
            {"name": "Brake service", "default_interval_km": 40000, "default_interval_days": 730},
            {"name": "Tire change", "default_interval_km": None, "default_interval_days": 180},
            {
                "name": "Annual inspection",
                "default_interval_km": None,
                "default_interval_days": 365,
            },
            {
                "name": "Air filter replacement",
                "default_interval_km": 30000,
                "default_interval_days": 730,
            },
            {
                "name": "Coolant service",
                "default_interval_km": 60000,
                "default_interval_days": 1460,
            },
            {
                "name": "Timing belt",
                "default_interval_km": 120000,
                "default_interval_days": 2555,
            },
            {
                "name": "Battery replacement",
                "default_interval_km": None,
                "default_interval_days": 1460,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("reminders")
    op.drop_table("record_parts")
    op.drop_table("stock_movements")
    op.drop_table("parts")
    op.drop_table("maintenance_records")
    op.drop_table("service_types")
    op.drop_table("vehicles")
