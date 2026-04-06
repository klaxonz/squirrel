"""add batch lookup index for thumbnail local index

Revision ID: c2f8a1d4b6e7
Revises: b7d4c2e9f1a0
Create Date: 2026-04-06 11:45:00.000000

"""
from alembic import op


revision = 'c2f8a1d4b6e7'
down_revision = 'b7d4c2e9f1a0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'ix_video_thumbnail_local_index_batch_exists',
        'video_thumbnail_local_index',
        ['batch_name', 'exists'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_video_thumbnail_local_index_batch_exists', table_name='video_thumbnail_local_index')
