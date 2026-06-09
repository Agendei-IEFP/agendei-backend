"""remove pending appointment status

Revision ID: b7e9f1a2c3d4
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b7e9f1a2c3d4"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE appointments SET status = 'confirmed' WHERE status = 'pending'")
    op.execute("ALTER TYPE statusenum RENAME TO statusenum_old")
    op.execute("CREATE TYPE statusenum AS ENUM ('confirmed', 'cancelled', 'completed')")
    op.execute(
        "ALTER TABLE appointments "
        "ALTER COLUMN status TYPE statusenum "
        "USING status::text::statusenum"
    )
    op.execute("DROP TYPE statusenum_old")
    op.execute("ALTER TABLE appointments ALTER COLUMN status SET DEFAULT 'confirmed'")


def downgrade() -> None:
    op.execute("ALTER TYPE statusenum RENAME TO statusenum_old")
    op.execute("CREATE TYPE statusenum AS ENUM ('pending', 'confirmed', 'cancelled', 'completed')")
    op.execute(
        "ALTER TABLE appointments "
        "ALTER COLUMN status TYPE statusenum "
        "USING status::text::statusenum"
    )
    op.execute("DROP TYPE statusenum_old")
    op.execute("ALTER TABLE appointments ALTER COLUMN status SET DEFAULT 'pending'")
