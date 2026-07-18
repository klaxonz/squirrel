"""add independent read and playback state to video history

Revision ID: c7e4a2b9d5f1
Revises: f3a9d6c1b8e2
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c7e4a2b9d5f1'
down_revision: str | None = 'f3a9d6c1b8e2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'video_history',
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        'video_history',
        sa.Column('has_playback', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        'ix_video_history_user_read',
        'video_history',
        ['user_id', 'is_read', 'video_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_video_history_user_read', table_name='video_history')
    op.drop_column('video_history', 'has_playback')
    op.drop_column('video_history', 'is_read')
