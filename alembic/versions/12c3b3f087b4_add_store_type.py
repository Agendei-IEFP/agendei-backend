"""add_store_type

Revision ID: 12c3b3f087b4
Revises: c33e0ff25fb3
Create Date: 2026-05-30 07:18:01.763247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12c3b3f087b4'
down_revision: Union[str, Sequence[str], None] = 'c33e0ff25fb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    storetype_enum = sa.Enum('hair_salon', 'barbershop', 'nails', 'aesthetics', 'massage', 'treatments', name='storetype')
    storetype_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('stores', sa.Column('store_type', storetype_enum, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('stores', 'store_type')
    sa.Enum(name='storetype').drop(op.get_bind(), checkfirst=True)
