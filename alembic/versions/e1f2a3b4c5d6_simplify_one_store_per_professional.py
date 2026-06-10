"""simplify: one store per professional, drop offerings and professional_stores

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-06-10 12:00:00.000000

Destructive migration for dev/Docker database.
Data in appointments and work_schedules is cleared.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear tables that reference columns being dropped/replaced
    op.execute("TRUNCATE TABLE appointments RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE work_schedules RESTART IDENTITY CASCADE")

    # professionals: add store_id
    op.add_column("professionals", sa.Column("store_id", sa.String(26), nullable=True))
    op.create_foreign_key(
        "fk_professionals_store_id",
        "professionals", "stores",
        ["store_id"], ["id"],
    )

    # services: rename default_price → price, default_duration_minutes → duration_minutes
    op.alter_column("services", "default_price", new_column_name="price")
    op.alter_column("services", "default_duration_minutes", new_column_name="duration_minutes")

    # work_schedules: drop professional_store_id, add professional_id, update unique constraint
    op.drop_constraint("uq_work_schedules_ps_weekday", "work_schedules", type_="unique")
    op.drop_column("work_schedules", "professional_store_id")
    op.add_column("work_schedules", sa.Column("professional_id", sa.String(26), nullable=True))
    op.create_foreign_key(
        "fk_work_schedules_professional_id",
        "work_schedules", "professionals",
        ["professional_id"], ["id"],
    )
    op.create_unique_constraint(
        "uq_work_schedules_prof_weekday",
        "work_schedules",
        ["professional_id", "weekday"],
    )

    # appointments: drop professional_store_id and offering_id, add service_id and store_id
    op.drop_column("appointments", "professional_store_id")
    op.drop_column("appointments", "offering_id")
    op.add_column("appointments", sa.Column("service_id", sa.String(26), nullable=True))
    op.add_column("appointments", sa.Column("store_id", sa.String(26), nullable=True))
    op.create_foreign_key(
        "fk_appointments_service_id",
        "appointments", "services",
        ["service_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_appointments_store_id",
        "appointments", "stores",
        ["store_id"], ["id"],
    )

    # drop offerings table (depends on professional_stores via professional_store_id)
    op.drop_table("offerings")

    # drop professional_stores table
    op.drop_table("professional_stores")


def downgrade() -> None:
    # Data is not preserved. This restores structure only.
    op.create_table(
        "professional_stores",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("professional_id", sa.String(26), sa.ForeignKey("professionals.id"), nullable=False),
        sa.Column("store_id", sa.String(26), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "offerings",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("service_id", sa.String(26), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("professional_store_id", sa.String(26), sa.ForeignKey("professional_stores.id"), nullable=False),
        sa.Column("price_override", sa.Numeric(10, 2), nullable=True),
        sa.Column("duration_override", sa.Integer(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.drop_column("appointments", "store_id")
    op.drop_column("appointments", "service_id")
    op.add_column("appointments", sa.Column("offering_id", sa.String(26), nullable=True))
    op.add_column("appointments", sa.Column("professional_store_id", sa.String(26), nullable=True))

    op.drop_constraint("uq_work_schedules_prof_weekday", "work_schedules", type_="unique")
    op.drop_column("work_schedules", "professional_id")
    op.add_column("work_schedules", sa.Column("professional_store_id", sa.String(26), nullable=True))
    op.create_unique_constraint(
        "uq_work_schedules_ps_weekday",
        "work_schedules",
        ["professional_store_id", "weekday"],
    )

    op.drop_constraint("fk_professionals_store_id", "professionals", type_="foreignkey")
    op.drop_column("professionals", "store_id")

    op.alter_column("services", "price", new_column_name="default_price")
    op.alter_column("services", "duration_minutes", new_column_name="default_duration_minutes")
