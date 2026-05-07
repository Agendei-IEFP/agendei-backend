"""professional multi store and invites

Revision ID: 18a779368dd3
Revises: 353a6feb39a8
Create Date: 2026-05-02 18:57:42.125244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '18a779368dd3'
down_revision: Union[str, Sequence[str], None] = '353a6feb39a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. professional_stores
    op.create_table(
        'professional_stores',
        sa.Column('professional_id', sa.String(length=26), nullable=False),
        sa.Column('store_id', sa.String(length=26), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['professional_id'], ['professionals.id']),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_professional_stores_pair_unique',
        'professional_stores',
        ['professional_id', 'store_id'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # 2. professional_invites
    op.create_table(
        'professional_invites',
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('store_id', sa.String(length=26), nullable=False),
        sa.Column('created_by', sa.String(length=26), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_user_id', sa.String(length=26), nullable=True),
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['accepted_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index(
        'ix_professional_invites_token',
        'professional_invites',
        ['token'],
    )

    # 3. Backfill: 1 ProfessionalStore per existing Professional, preserving created_at.
    # 26-char id derived from gen_random_uuid() (built-in PG13+, no pgcrypto needed).
    # Shape doesn't have to be a real ULID for backfilled rows — uniqueness is what matters.
    op.execute("""
        INSERT INTO professional_stores (id, professional_id, store_id, is_active, created_at, updated_at, deleted_at)
        SELECT
            substr(replace(gen_random_uuid()::text, '-', ''), 1, 26),
            p.id,
            p.store_id,
            true,
            p.created_at,
            p.created_at,
            NULL
        FROM professionals p
        WHERE p.deleted_at IS NULL
    """)

    # 4. Drop professionals.store_id (FK + column)
    # Find FK name dynamically — initial migration didn't name it, so let Postgres find it.
    op.execute("""
        DO $$
        DECLARE
            fk_name text;
        BEGIN
            SELECT conname INTO fk_name
            FROM pg_constraint
            WHERE conrelid = 'professionals'::regclass
              AND contype = 'f'
              AND conkey = ARRAY[(
                  SELECT attnum FROM pg_attribute
                  WHERE attrelid = 'professionals'::regclass AND attname = 'store_id'
              )];
            IF fk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE professionals DROP CONSTRAINT %I', fk_name);
            END IF;
        END $$;
    """)
    op.drop_column('professionals', 'store_id')

    # 5. Partial unique index on professionals.user_id
    op.create_index(
        'ix_professionals_user_id_unique',
        'professionals',
        ['user_id'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # 6. offerings: add professional_store_id, backfill from professional_stores, drop professional_id
    op.add_column('offerings', sa.Column('professional_store_id', sa.String(length=26), nullable=True))
    op.execute("""
        UPDATE offerings o
        SET professional_store_id = ps.id
        FROM professional_stores ps
        WHERE ps.professional_id = o.professional_id
          AND ps.deleted_at IS NULL
    """)
    op.create_foreign_key(
        'fk_offerings_professional_store_id',
        'offerings',
        'professional_stores',
        ['professional_store_id'],
        ['id'],
    )
    op.execute("""
        DO $$
        DECLARE
            fk_name text;
        BEGIN
            SELECT conname INTO fk_name
            FROM pg_constraint
            WHERE conrelid = 'offerings'::regclass
              AND contype = 'f'
              AND conkey = ARRAY[(
                  SELECT attnum FROM pg_attribute
                  WHERE attrelid = 'offerings'::regclass AND attname = 'professional_id'
              )];
            IF fk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE offerings DROP CONSTRAINT %I', fk_name);
            END IF;
        END $$;
    """)
    op.drop_column('offerings', 'professional_id')
    op.alter_column('offerings', 'professional_store_id', nullable=False)

    # 7. work_schedules: same shape as offerings
    op.add_column('work_schedules', sa.Column('professional_store_id', sa.String(length=26), nullable=True))
    op.execute("""
        UPDATE work_schedules w
        SET professional_store_id = ps.id
        FROM professional_stores ps
        WHERE ps.professional_id = w.professional_id
          AND ps.deleted_at IS NULL
    """)
    op.create_foreign_key(
        'fk_work_schedules_professional_store_id',
        'work_schedules',
        'professional_stores',
        ['professional_store_id'],
        ['id'],
    )
    op.execute("""
        DO $$
        DECLARE
            fk_name text;
        BEGIN
            SELECT conname INTO fk_name
            FROM pg_constraint
            WHERE conrelid = 'work_schedules'::regclass
              AND contype = 'f'
              AND conkey = ARRAY[(
                  SELECT attnum FROM pg_attribute
                  WHERE attrelid = 'work_schedules'::regclass AND attname = 'professional_id'
              )];
            IF fk_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE work_schedules DROP CONSTRAINT %I', fk_name);
            END IF;
        END $$;
    """)
    op.drop_column('work_schedules', 'professional_id')
    op.alter_column('work_schedules', 'professional_store_id', nullable=False)

    # 8. appointments: add professional_store_id (KEEP professional_id denormalized)
    op.add_column('appointments', sa.Column('professional_store_id', sa.String(length=26), nullable=True))
    op.execute("""
        UPDATE appointments a
        SET professional_store_id = ps.id
        FROM professional_stores ps
        WHERE ps.professional_id = a.professional_id
          AND ps.deleted_at IS NULL
    """)
    op.create_foreign_key(
        'fk_appointments_professional_store_id',
        'appointments',
        'professional_stores',
        ['professional_store_id'],
        ['id'],
    )
    op.alter_column('appointments', 'professional_store_id', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # appointments: drop professional_store_id, keep existing professional_id intact
    op.drop_constraint('fk_appointments_professional_store_id', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'professional_store_id')

    # work_schedules: re-add professional_id, backfill, drop professional_store_id
    op.add_column('work_schedules', sa.Column('professional_id', sa.String(length=26), nullable=True))
    op.execute("""
        UPDATE work_schedules w
        SET professional_id = ps.professional_id
        FROM professional_stores ps
        WHERE ps.id = w.professional_store_id
    """)
    op.create_foreign_key('fk_work_schedules_professional_id', 'work_schedules', 'professionals', ['professional_id'], ['id'])
    op.alter_column('work_schedules', 'professional_id', nullable=False)
    op.drop_constraint('fk_work_schedules_professional_store_id', 'work_schedules', type_='foreignkey')
    op.drop_column('work_schedules', 'professional_store_id')

    # offerings: same as work_schedules
    op.add_column('offerings', sa.Column('professional_id', sa.String(length=26), nullable=True))
    op.execute("""
        UPDATE offerings o
        SET professional_id = ps.professional_id
        FROM professional_stores ps
        WHERE ps.id = o.professional_store_id
    """)
    op.create_foreign_key('fk_offerings_professional_id', 'offerings', 'professionals', ['professional_id'], ['id'])
    op.alter_column('offerings', 'professional_id', nullable=False)
    op.drop_constraint('fk_offerings_professional_store_id', 'offerings', type_='foreignkey')
    op.drop_column('offerings', 'professional_store_id')

    # professionals: drop partial index, restore store_id from junction
    op.drop_index('ix_professionals_user_id_unique', table_name='professionals')
    op.add_column('professionals', sa.Column('store_id', sa.String(length=26), nullable=True))
    op.execute("""
        UPDATE professionals p
        SET store_id = ps.store_id
        FROM professional_stores ps
        WHERE ps.professional_id = p.id
          AND ps.deleted_at IS NULL
    """)
    op.create_foreign_key('fk_professionals_store_id', 'professionals', 'stores', ['store_id'], ['id'])
    op.alter_column('professionals', 'store_id', nullable=False)

    # drop new tables
    op.drop_index('ix_professional_invites_token', table_name='professional_invites')
    op.drop_table('professional_invites')

    op.drop_index('ix_professional_stores_pair_unique', table_name='professional_stores')
    op.drop_table('professional_stores')
