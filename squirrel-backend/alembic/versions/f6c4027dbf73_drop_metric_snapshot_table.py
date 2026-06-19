"""drop_metric_snapshot_table

The metric persistence pipeline (MetricsService + scheduled collection/cleanup
tasks + MetricSnapshot ORM model) has been removed; the realtime Redis layer is
the only consumer of metrics now. Drop the unused long-term storage table.

Revision ID: f6c4027dbf73
Revises: e8a2c4d6f7b5
Create Date: 2026-06-17 23:30:56.126240

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'f6c4027dbf73'
down_revision = 'e8a2c4d6f7b5'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('ix_metric_type', table_name='metric_snapshot')
    op.drop_index('ix_metric_timestamp', table_name='metric_snapshot')
    op.drop_index(op.f('ix_metric_snapshot_timestamp'), table_name='metric_snapshot')
    op.drop_index('ix_metric_name_timestamp', table_name='metric_snapshot')
    op.drop_index('ix_metric_labels', table_name='metric_snapshot', postgresql_using='gin')
    op.drop_table('metric_snapshot')


def downgrade():
    op.create_table(
        'metric_snapshot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.VARCHAR(length=128), nullable=False),
        sa.Column('metric_type', sa.VARCHAR(length=32), nullable=False),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('value', sa.DECIMAL(precision=20, scale=6), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_metric_labels', 'metric_snapshot', ['labels'], unique=False, postgresql_using='gin')
    op.create_index('ix_metric_name_timestamp', 'metric_snapshot', ['metric_name', 'timestamp'], unique=False)
    op.create_index(op.f('ix_metric_snapshot_timestamp'), 'metric_snapshot', ['timestamp'], unique=False)
    op.create_index('ix_metric_timestamp', 'metric_snapshot', ['timestamp'], unique=False)
    op.create_index('ix_metric_type', 'metric_snapshot', ['metric_type'], unique=False)
