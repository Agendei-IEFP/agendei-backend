"""simplify work schedules: drop store_availabilities, one block per day

Revision ID: d1e2f3a4b5c6
Revises: c33e0ff25fb3
Create Date: 2026-06-09 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "b7e9f1a2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("store_availabilities")

    # Remove duplicate (professional_store_id, weekday) rows — keep the one with the lowest id
    op.execute("""
        DELETE FROM work_schedules
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM work_schedules
            GROUP BY professional_store_id, weekday
        )
    """)

    op.create_unique_constraint(
        "uq_work_schedules_ps_weekday",
        "work_schedules",
        ["professional_store_id", "weekday"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_work_schedules_ps_weekday", "work_schedules", type_="unique")

    op.create_table(
        "store_availabilities",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "professional_store_id",
            sa.String(26),
            sa.ForeignKey("professional_stores.id"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
