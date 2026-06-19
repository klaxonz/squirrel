"""drop_scheduler_status_legacy_tasks

Revision ID: d3b72f9a4c61
Revises: f8a2b7c9d0e1
Create Date: 2026-06-07 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = 'd3b72f9a4c61'
down_revision = 'f8a2b7c9d0e1'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('scheduler_status', 'legacy_tasks')


def downgrade():
    op.add_column(
        'scheduler_status',
        sa.Column('legacy_tasks', sa.JSON(), nullable=False, server_default='{}', comment='传统任务信息'),
    )
