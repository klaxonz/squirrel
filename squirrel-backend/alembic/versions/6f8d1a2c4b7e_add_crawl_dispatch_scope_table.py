"""add_crawl_dispatch_scope_table

Revision ID: 6f8d1a2c4b7e
Revises: 0f7c3b2a91de
Create Date: 2026-04-01 16:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = '6f8d1a2c4b7e'
down_revision = '0f7c3b2a91de'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'crawl_dispatch_scope',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('scope_type', sa.VARCHAR(length=32), nullable=False),
        sa.Column('scope_key', sa.VARCHAR(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scope_type', 'scope_key', name='uq_crawl_dispatch_scope_type_key'),
    )
    op.create_index(
        'ix_crawl_dispatch_scope_type_key',
        'crawl_dispatch_scope',
        ['scope_type', 'scope_key'],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO crawl_dispatch_scope (scope_type, scope_key, created_at)
            SELECT DISTINCT 'site', site, NOW()
            FROM crawl_task
            WHERE site IS NOT NULL
            ON CONFLICT (scope_type, scope_key) DO NOTHING
            """,
        ),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO crawl_dispatch_scope (scope_type, scope_key, created_at)
            SELECT DISTINCT 'task_type', task_type, NOW()
            FROM crawl_task
            WHERE task_type IS NOT NULL
            ON CONFLICT (scope_type, scope_key) DO NOTHING
            """,
        ),
    )


def downgrade():
    op.drop_index('ix_crawl_dispatch_scope_type_key', table_name='crawl_dispatch_scope')
    op.drop_table('crawl_dispatch_scope')
