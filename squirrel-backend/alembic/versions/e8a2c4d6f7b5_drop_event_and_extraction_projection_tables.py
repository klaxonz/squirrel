"""drop_event_and_extraction_projection_tables

Revision ID: e8a2c4d6f7b5
Revises: d5e7f9a1b3c4
Create Date: 2026-06-14 22:00:00.000000

Drops the append-only ``subscription_sync_event`` log and the
``video_extraction_projection`` read model.

After the SyncCenter dashboard / history / extraction-center removal, both tables
became write-only orphans:
- ``subscription_sync_event`` was read only by its own ``next_seq_no`` allocator
  (a self-referential seq-no ritual); no consumer ever queried events back.
- ``video_extraction_projection`` was refreshed on every video-extract task
  transition but had zero readers once the extraction-center dashboard was removed.

The sync state machine continues to track state on ``subscription_sync_state``;
``run_id`` survives as a pure correlation ID (CrawlTask payload / API responses).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'e8a2c4d6f7b5'
down_revision = 'd5e7f9a1b3c4'
branch_labels = None
depends_on = None


def upgrade():
    # subscription_sync_event
    op.drop_index('ix_subscription_sync_event_run_lookup', table_name='subscription_sync_event')
    op.drop_index('ix_subscription_sync_event_trace_id', table_name='subscription_sync_event')
    op.drop_index('ix_subscription_sync_event_request_id', table_name='subscription_sync_event')
    op.drop_index('ix_subscription_sync_event_type_time', table_name='subscription_sync_event')
    op.drop_index('ix_subscription_sync_event_site_time', table_name='subscription_sync_event')
    op.drop_index('ix_subscription_sync_event_subscription_time', table_name='subscription_sync_event')
    op.drop_index('ix_subscription_sync_event_stream_id', table_name='subscription_sync_event')
    op.drop_table('subscription_sync_event')

    # video_extraction_projection
    op.drop_index(
        'ix_video_extraction_projection_status_locked_at',
        table_name='video_extraction_projection',
    )
    op.drop_index(
        'ix_video_extraction_projection_status_queued_at',
        table_name='video_extraction_projection',
    )
    op.drop_index(
        'ix_video_extraction_projection_status_updated',
        table_name='video_extraction_projection',
    )
    op.drop_index(
        'ix_video_extraction_projection_updated_at',
        table_name='video_extraction_projection',
    )
    op.drop_index(
        'ix_video_extraction_projection_display_status',
        table_name='video_extraction_projection',
    )
    op.drop_index(
        'ix_video_extraction_projection_subscription_id',
        table_name='video_extraction_projection',
    )
    op.drop_table('video_extraction_projection')


def downgrade():
    # Recreate empty table structures (rows are not repopulated).
    # Mirrors f2c4b6a8d001 (subscription_sync_event) and a1b2c3d4e5f6 (video_extraction_projection).
    op.create_table(
        'video_extraction_projection',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('group_kind', sa.VARCHAR(length=16), nullable=False),
        sa.Column('group_value', sa.VARCHAR(length=64), nullable=False),
        sa.Column('site', sa.VARCHAR(length=64), nullable=True),
        sa.Column('sync_status', sa.VARCHAR(length=16), nullable=False, server_default='idle'),
        sa.Column('display_status', sa.VARCHAR(length=16), nullable=False, server_default='healthy'),
        sa.Column('current_phase', sa.VARCHAR(length=32), nullable=True),
        sa.Column('last_error', sa.TEXT(), nullable=True),
        sa.Column('queued_at', sa.DateTime(), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('last_success_at', sa.DateTime(), nullable=True),
        sa.Column('pending_video_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('batch_task_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('queued_task_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('running_task_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_task_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_task_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'subscription_id',
            'group_kind',
            'group_value',
            name='uix_video_extraction_projection_group',
        ),
    )
    op.create_index(
        'ix_video_extraction_projection_subscription_id',
        'video_extraction_projection',
        ['subscription_id'],
        unique=False,
    )
    op.create_index(
        'ix_video_extraction_projection_display_status',
        'video_extraction_projection',
        ['display_status'],
        unique=False,
    )
    op.create_index(
        'ix_video_extraction_projection_updated_at',
        'video_extraction_projection',
        ['updated_at'],
        unique=False,
    )
    op.create_index(
        'ix_video_extraction_projection_status_updated',
        'video_extraction_projection',
        ['display_status', 'updated_at'],
        unique=False,
    )
    op.create_index(
        'ix_video_extraction_projection_status_queued_at',
        'video_extraction_projection',
        ['display_status', 'queued_at'],
        unique=False,
    )
    op.create_index(
        'ix_video_extraction_projection_status_locked_at',
        'video_extraction_projection',
        ['display_status', 'locked_at'],
        unique=False,
    )

    op.create_table(
        'subscription_sync_event',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stream_id', sa.VARCHAR(length=64), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('sync_state_id', sa.Integer(), nullable=True),
        sa.Column('site', sa.VARCHAR(length=64), nullable=True),
        sa.Column('sync_mode', sa.VARCHAR(length=16), nullable=False),
        sa.Column('trigger', sa.VARCHAR(length=32), nullable=True),
        sa.Column('request_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('trace_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('event_type', sa.VARCHAR(length=64), nullable=False),
        sa.Column('event_phase', sa.VARCHAR(length=32), nullable=True),
        sa.Column('event_status', sa.VARCHAR(length=16), nullable=True),
        sa.Column('seq_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payload', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('message', sa.TEXT(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.Column('projected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stream_id', 'seq_no', name='uix_subscription_sync_event_stream_seq'),
    )
    op.create_index('ix_subscription_sync_event_stream_id', 'subscription_sync_event', ['stream_id'], unique=False)
    op.create_index(
        'ix_subscription_sync_event_subscription_time',
        'subscription_sync_event',
        ['subscription_id', 'occurred_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_event_site_time',
        'subscription_sync_event',
        ['site', 'occurred_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_event_type_time',
        'subscription_sync_event',
        ['event_type', 'occurred_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_event_run_lookup',
        'subscription_sync_event',
        ['subscription_id', 'sync_state_id', 'occurred_at'],
        unique=False,
    )
    op.create_index('ix_subscription_sync_event_request_id', 'subscription_sync_event', ['request_id'], unique=False)
    op.create_index('ix_subscription_sync_event_trace_id', 'subscription_sync_event', ['trace_id'], unique=False)
