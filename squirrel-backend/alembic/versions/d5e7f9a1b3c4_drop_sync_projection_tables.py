"""drop_sync_projection_tables

Revision ID: d5e7f9a1b3c4
Revises: b2c3d4e5f6a7
Create Date: 2026-06-14 21:00:00.000000

Drops the subscription sync dashboard projection tables (run / subscription / trend).
These were read only by the (now-removed) sync dashboard / history feature and the
retry-wait reconciliation job. The core ``subscription_sync_event`` append-only log
is retained — ``run_service.next_seq_no`` still reads it to allocate event sequence
numbers, and the event stream remains the system's source of truth for sync runs.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'd5e7f9a1b3c4'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # trend
    op.drop_index('ix_subscription_sync_trend_dims_bucket', table_name='subscription_sync_trend_projection')
    op.drop_index('ix_subscription_sync_trend_site_bucket', table_name='subscription_sync_trend_projection')
    op.drop_index('ix_subscription_sync_trend_bucket_time', table_name='subscription_sync_trend_projection')
    op.drop_table('subscription_sync_trend_projection')

    # subscription
    op.drop_index(
        'ix_subscription_sync_subscription_projection_status_next_sync',
        table_name='subscription_sync_subscription_projection',
    )
    op.drop_index(
        'ix_subscription_sync_subscription_projection_updated_at',
        table_name='subscription_sync_subscription_projection',
    )
    op.drop_index(
        'ix_subscription_sync_subscription_projection_next_sync',
        table_name='subscription_sync_subscription_projection',
    )
    op.drop_index(
        'ix_subscription_sync_subscription_projection_status',
        table_name='subscription_sync_subscription_projection',
    )
    op.drop_table('subscription_sync_subscription_projection')

    # run
    op.drop_index(
        'ix_subscription_sync_run_projection_subscription_started',
        table_name='subscription_sync_run_projection',
    )
    op.drop_index(
        'ix_subscription_sync_run_projection_subscription_time',
        table_name='subscription_sync_run_projection',
    )
    op.drop_index('ix_subscription_sync_run_projection_finished_at', table_name='subscription_sync_run_projection')
    op.drop_index('ix_subscription_sync_run_projection_started_at', table_name='subscription_sync_run_projection')
    op.drop_index('ix_subscription_sync_run_projection_site_time', table_name='subscription_sync_run_projection')
    op.drop_index('ix_subscription_sync_run_projection_status_time', table_name='subscription_sync_run_projection')
    op.drop_index('ix_subscription_sync_run_projection_subscription', table_name='subscription_sync_run_projection')
    op.drop_table('subscription_sync_run_projection')


def downgrade():
    # Recreate empty projection table structures (rows are not repopulated).
    # Mirrors f2c4b6a8d001's original definitions.
    op.create_table(
        'subscription_sync_run_projection',
        sa.Column('run_id', sa.VARCHAR(length=64), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('sync_state_id', sa.Integer(), nullable=True),
        sa.Column('site', sa.VARCHAR(length=64), nullable=True),
        sa.Column('sync_mode', sa.VARCHAR(length=16), nullable=False),
        sa.Column('trigger', sa.VARCHAR(length=32), nullable=True),
        sa.Column('request_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('trace_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('status', sa.VARCHAR(length=16), nullable=False, server_default='created'),
        sa.Column('current_phase', sa.VARCHAR(length=32), nullable=True),
        sa.Column('queued_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_type', sa.VARCHAR(length=64), nullable=True),
        sa.Column('error_message', sa.VARCHAR(length=1024), nullable=True),
        sa.Column('videos_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_enqueued', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_extracted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pending_video_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_event_seq_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_event_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('run_id'),
    )
    op.create_index(
        'ix_subscription_sync_run_projection_subscription',
        'subscription_sync_run_projection',
        ['subscription_id'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_run_projection_status_time',
        'subscription_sync_run_projection',
        ['status', 'last_event_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_run_projection_site_time',
        'subscription_sync_run_projection',
        ['site', 'last_event_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_run_projection_started_at',
        'subscription_sync_run_projection',
        ['started_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_run_projection_finished_at',
        'subscription_sync_run_projection',
        ['finished_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_run_projection_subscription_time',
        'subscription_sync_run_projection',
        ['subscription_id', 'last_event_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_run_projection_subscription_started',
        'subscription_sync_run_projection',
        ['subscription_id', 'started_at'],
        unique=False,
    )

    op.create_table(
        'subscription_sync_subscription_projection',
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('latest_run_id', sa.VARCHAR(length=64), nullable=True),
        sa.Column('current_status', sa.VARCHAR(length=16), nullable=False, server_default='idle'),
        sa.Column('current_phase', sa.VARCHAR(length=32), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_success_at', sa.DateTime(), nullable=True),
        sa.Column('next_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_error_message', sa.VARCHAR(length=1024), nullable=True),
        sa.Column('pending_video_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_event_seq_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('subscription_id'),
    )
    op.create_index(
        'ix_subscription_sync_subscription_projection_status',
        'subscription_sync_subscription_projection',
        ['current_status'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_subscription_projection_next_sync',
        'subscription_sync_subscription_projection',
        ['next_sync_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_subscription_projection_updated_at',
        'subscription_sync_subscription_projection',
        ['updated_at'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_subscription_projection_status_next_sync',
        'subscription_sync_subscription_projection',
        ['current_status', 'next_sync_at'],
        unique=False,
    )

    op.create_table(
        'subscription_sync_trend_projection',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('bucket_time', sa.DateTime(), nullable=False),
        sa.Column('bucket_granularity', sa.VARCHAR(length=16), nullable=False, server_default='hour'),
        sa.Column('site', sa.VARCHAR(length=64), nullable=False, server_default=''),
        sa.Column('sync_mode', sa.VARCHAR(length=16), nullable=False, server_default=''),
        sa.Column('trigger', sa.VARCHAR(length=32), nullable=False, server_default=''),
        sa.Column('runs_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('runs_success', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('runs_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('runs_deferred', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_enqueued', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_extracted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('videos_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_total_ms', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('avg_duration_ms', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('p95_duration_ms', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('duration_histogram', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'bucket_time',
            'bucket_granularity',
            'site',
            'sync_mode',
            'trigger',
            name='uix_subscription_sync_trend_bucket_dims',
        ),
    )
    op.create_index(
        'ix_subscription_sync_trend_bucket_time', 'subscription_sync_trend_projection', ['bucket_time'], unique=False
    )
    op.create_index(
        'ix_subscription_sync_trend_site_bucket',
        'subscription_sync_trend_projection',
        ['site', 'bucket_time'],
        unique=False,
    )
    op.create_index(
        'ix_subscription_sync_trend_dims_bucket',
        'subscription_sync_trend_projection',
        ['site', 'sync_mode', 'trigger', 'bucket_time'],
        unique=False,
    )
