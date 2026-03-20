"""add_subscription_sync_state_table

Revision ID: 4c7a3b8f2d11
Revises: c16114e79cd2
Create Date: 2026-03-21 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '4c7a3b8f2d11'
down_revision = 'c16114e79cd2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'subscription_sync_state',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('site', sa.VARCHAR(length=64), nullable=True),
        sa.Column('sync_mode', sa.VARCHAR(length=16), nullable=False),
        sa.Column('sync_status', sa.VARCHAR(length=16), nullable=False),
        sa.Column('cursor_payload', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('last_seen_video_url', sa.VARCHAR(length=2048), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_success_at', sa.DateTime(), nullable=True),
        sa.Column('next_sync_at', sa.DateTime(), nullable=False),
        sa.Column('queued_at', sa.DateTime(), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('queue_token', sa.VARCHAR(length=64), nullable=True),
        sa.Column('pending_video_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscription_id', 'sync_mode', name='uix_subscription_sync_state_sub_mode')
    )
    op.create_index('ix_subscription_sync_state_subscription_id', 'subscription_sync_state', ['subscription_id'], unique=False)
    op.create_index('ix_subscription_sync_state_sync_status', 'subscription_sync_state', ['sync_status'], unique=False)
    op.create_index('ix_subscription_sync_state_next_sync_at', 'subscription_sync_state', ['next_sync_at'], unique=False)
    op.create_index(
        'ix_subscription_sync_state_due_lookup',
        'subscription_sync_state',
        ['sync_mode', 'sync_status', 'next_sync_at'],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO subscription_sync_state (
            subscription_id,
            sync_mode,
            sync_status,
            cursor_payload,
            next_sync_at,
            pending_video_count,
            failure_count,
            version,
            created_at,
            updated_at
        )
        SELECT
            s.id,
            'incremental',
            'idle',
            '{}'::json,
            NOW(),
            0,
            0,
            0,
            NOW(),
            NOW()
        FROM subscription s
        WHERE s.is_deleted IS FALSE
          AND s.url IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO subscription_sync_state (
            subscription_id,
            sync_mode,
            sync_status,
            cursor_payload,
            next_sync_at,
            pending_video_count,
            failure_count,
            version,
            created_at,
            updated_at
        )
        SELECT
            s.id,
            'full',
            'idle',
            '{}'::json,
            NOW(),
            0,
            0,
            0,
            NOW(),
            NOW()
        FROM subscription s
        WHERE s.is_deleted IS FALSE
          AND s.url IS NOT NULL
        """
    )


def downgrade():
    op.drop_index('ix_subscription_sync_state_due_lookup', table_name='subscription_sync_state')
    op.drop_index('ix_subscription_sync_state_next_sync_at', table_name='subscription_sync_state')
    op.drop_index('ix_subscription_sync_state_sync_status', table_name='subscription_sync_state')
    op.drop_index('ix_subscription_sync_state_subscription_id', table_name='subscription_sync_state')
    op.drop_table('subscription_sync_state')
