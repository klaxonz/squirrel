"""add_outbox_event_and_gap_state_fields

Revision ID: 9f1c2d3e4b5a
Revises: 6f8d1a2c4b7e
Create Date: 2026-04-04 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f1c2d3e4b5a'
down_revision = '6f8d1a2c4b7e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'outbox_event',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.VARCHAR(length=64), nullable=False),
        sa.Column('event_key', sa.VARCHAR(length=255), nullable=False),
        sa.Column('aggregate_type', sa.VARCHAR(length=64), nullable=False),
        sa.Column('aggregate_id', sa.VARCHAR(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.VARCHAR(length=16), nullable=False),
        sa.Column('priority', sa.VARCHAR(length=16), nullable=False),
        sa.Column('available_at', sa.DateTime(), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('locked_by', sa.VARCHAR(length=64), nullable=True),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.TEXT(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_key', name='uix_outbox_event_event_key'),
    )
    op.create_index('ix_outbox_event_status_available', 'outbox_event', ['status', 'available_at'], unique=False)
    op.create_index(
        'ix_outbox_event_aggregate_lookup',
        'outbox_event',
        ['aggregate_type', 'aggregate_id', 'created_at'],
        unique=False,
    )

    op.add_column('subscription_sync_state', sa.Column('last_head_sample_urls', sa.JSON(), nullable=True))
    op.add_column('subscription_sync_state', sa.Column('last_head_fingerprint', sa.VARCHAR(length=64), nullable=True))
    op.add_column('subscription_sync_state', sa.Column('last_known_total_available', sa.Integer(), nullable=True))
    op.add_column(
        'subscription_sync_state',
        sa.Column('gap_suspicion_score', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('subscription_sync_state', sa.Column('gap_suspicion_reason', sa.TEXT(), nullable=True))
    op.add_column('subscription_sync_state', sa.Column('last_gap_detected_at', sa.DateTime(), nullable=True))
    op.add_column('subscription_sync_state', sa.Column('last_full_requested_at', sa.DateTime(), nullable=True))
    op.add_column(
        'subscription_sync_state',
        sa.Column('head_anchor_missing_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.alter_column('subscription_sync_state', 'gap_suspicion_score', server_default=None)
    op.alter_column('subscription_sync_state', 'head_anchor_missing_count', server_default=None)


def downgrade():
    op.drop_column('subscription_sync_state', 'head_anchor_missing_count')
    op.drop_column('subscription_sync_state', 'last_full_requested_at')
    op.drop_column('subscription_sync_state', 'last_gap_detected_at')
    op.drop_column('subscription_sync_state', 'gap_suspicion_reason')
    op.drop_column('subscription_sync_state', 'gap_suspicion_score')
    op.drop_column('subscription_sync_state', 'last_known_total_available')
    op.drop_column('subscription_sync_state', 'last_head_fingerprint')
    op.drop_column('subscription_sync_state', 'last_head_sample_urls')

    op.drop_index('ix_outbox_event_aggregate_lookup', table_name='outbox_event')
    op.drop_index('ix_outbox_event_status_available', table_name='outbox_event')
    op.drop_table('outbox_event')
