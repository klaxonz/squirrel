"""add crawl task sync state id

Revision ID: a4d9b6e2c731
Revises: e9a1f3c7d4b8
Create Date: 2026-07-11 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = 'a4d9b6e2c731'
down_revision = 'e9a1f3c7d4b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('crawl_task', sa.Column('sync_state_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE crawl_task
        SET sync_state_id = CAST(payload ->> 'sync_state_id' AS INTEGER)
        WHERE payload ->> 'sync_state_id' IS NOT NULL
          AND payload ->> 'sync_state_id' ~ '^[0-9]+$'
        """
    )
    op.create_index(
        'ix_crawl_task_sync_state_type_status',
        'crawl_task',
        ['sync_state_id', 'task_type', 'status'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_crawl_task_sync_state_type_status', table_name='crawl_task')
    op.drop_column('crawl_task', 'sync_state_id')
