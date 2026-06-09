"""store_type_to_store_types_array

Revision ID: a1b2c3d4e5f6
Revises: 12c3b3f087b4
Create Date: 2026-06-02 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '12c3b3f087b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

storetype_enum = postgresql.ENUM(
    'hair_salon', 'barbershop', 'nails', 'aesthetics', 'massage', 'treatments',
    name='storetype',
    create_type=False,
)


def upgrade() -> None:
    op.drop_column('stores', 'store_type')
    op.add_column(
        'stores',
        sa.Column(
            'store_types',
            postgresql.ARRAY(storetype_enum),
            nullable=False,
            server_default='{}',
        ),
    )


def downgrade() -> None:
    op.drop_column('stores', 'store_types')
    op.add_column(
        'stores',
        sa.Column('store_type', storetype_enum, nullable=True),
    )
