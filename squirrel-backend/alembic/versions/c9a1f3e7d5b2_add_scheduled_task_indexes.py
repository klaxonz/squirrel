"""add scheduled task indexes

Revision ID: c9a1f3e7d5b2
Revises: 8b6a1d5e3c4f
Create Date: 2026-05-15 00:00:00.000000

"""

from alembic import op

revision = 'c9a1f3e7d5b2'
down_revision = '8b6a1d5e3c4f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_scheduled_task_status_created', 'scheduled_task', ['status', 'created_at'], unique=False)
    op.create_index('ix_scheduled_task_type_created', 'scheduled_task', ['task_type', 'created_at'], unique=False)
    op.create_index('ix_scheduled_task_created_at', 'scheduled_task', ['created_at'], unique=False)
    op.create_index('ix_task_execution_log_started_at', 'task_execution_log', ['started_at'], unique=False)
    op.create_index('ix_task_execution_log_task_started', 'task_execution_log', ['task_id', 'started_at'], unique=False)


def downgrade():
    op.drop_index('ix_task_execution_log_task_started', table_name='task_execution_log')
    op.drop_index('ix_task_execution_log_started_at', table_name='task_execution_log')
    op.drop_index('ix_scheduled_task_created_at', table_name='scheduled_task')
    op.drop_index('ix_scheduled_task_type_created', table_name='scheduled_task')
    op.drop_index('ix_scheduled_task_status_created', table_name='scheduled_task')
