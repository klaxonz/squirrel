"""add_idle_sync_count_to_subscription_sync_state

Revision ID: 662a2b1c9d44
Revises: 4c7a3b8f2d11
Create Date: 2026-03-21 15:20:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = "662a2b1c9d44"
down_revision = "4c7a3b8f2d11"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "subscription_sync_state",
        sa.Column("idle_sync_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("subscription_sync_state", "idle_sync_count")
