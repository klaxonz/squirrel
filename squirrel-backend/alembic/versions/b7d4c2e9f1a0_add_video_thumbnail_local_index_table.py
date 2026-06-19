"""add video thumbnail local index table

Revision ID: b7d4c2e9f1a0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-06 11:10:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = 'b7d4c2e9f1a0'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'video_thumbnail_local_index',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('batch_name', sa.VARCHAR(length=32), nullable=False),
        sa.Column('filename', sa.VARCHAR(length=255), nullable=False),
        sa.Column('exists', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('indexed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ux_video_thumbnail_local_index_video_id',
        'video_thumbnail_local_index',
        ['video_id'],
        unique=True,
    )
    op.create_index(
        'ix_video_thumbnail_local_index_exists_indexed',
        'video_thumbnail_local_index',
        ['exists', 'indexed_at'],
        unique=False,
    )
    op.create_index(
        'ix_video_thumbnail_local_index_updated_at',
        'video_thumbnail_local_index',
        ['updated_at'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_video_thumbnail_local_index_updated_at', table_name='video_thumbnail_local_index')
    op.drop_index('ix_video_thumbnail_local_index_exists_indexed', table_name='video_thumbnail_local_index')
    op.drop_index('ux_video_thumbnail_local_index_video_id', table_name='video_thumbnail_local_index')
    op.drop_table('video_thumbnail_local_index')
