"""add_gap_state_fields

Revision ID: 9f1c2d3e4b5a
Revises: 6f8d1a2c4b7e
Create Date: 2026-04-04 14:20:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9f1c2d3e4b5a"
down_revision = "6f8d1a2c4b7e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("subscription_sync_state", sa.Column("last_head_sample_urls", sa.JSON(), nullable=True))
    op.add_column("subscription_sync_state", sa.Column("last_head_fingerprint", sa.VARCHAR(length=64), nullable=True))
    op.add_column("subscription_sync_state", sa.Column("last_known_total_available", sa.Integer(), nullable=True))
    op.add_column(
        "subscription_sync_state",
        sa.Column("gap_suspicion_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("subscription_sync_state", sa.Column("gap_suspicion_reason", sa.TEXT(), nullable=True))
    op.add_column("subscription_sync_state", sa.Column("last_gap_detected_at", sa.DateTime(), nullable=True))
    op.add_column("subscription_sync_state", sa.Column("last_full_requested_at", sa.DateTime(), nullable=True))
    op.add_column(
        "subscription_sync_state",
        sa.Column("head_anchor_missing_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("subscription_sync_state", "gap_suspicion_score", server_default=None)
    op.alter_column("subscription_sync_state", "head_anchor_missing_count", server_default=None)


def downgrade():
    op.drop_column("subscription_sync_state", "head_anchor_missing_count")
    op.drop_column("subscription_sync_state", "last_full_requested_at")
    op.drop_column("subscription_sync_state", "last_gap_detected_at")
    op.drop_column("subscription_sync_state", "gap_suspicion_reason")
    op.drop_column("subscription_sync_state", "gap_suspicion_score")
    op.drop_column("subscription_sync_state", "last_known_total_available")
    op.drop_column("subscription_sync_state", "last_head_fingerprint")
    op.drop_column("subscription_sync_state", "last_head_sample_urls")
