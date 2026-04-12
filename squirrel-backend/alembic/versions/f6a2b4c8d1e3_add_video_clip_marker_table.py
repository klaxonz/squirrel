"""add video clip marker table

Revision ID: f6a2b4c8d1e3
Revises: e4f2a6b1c9d0
Create Date: 2026-04-12 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f6a2b4c8d1e3'
down_revision = 'e4f2a6b1c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'video_clip_marker',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('start_time', sa.Float(), nullable=False, server_default='0'),
        sa.Column('end_time', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_clip_marker_user_id'), 'video_clip_marker', ['user_id'], unique=False)
    op.create_index('ix_video_clip_marker_user_video', 'video_clip_marker', ['user_id', 'video_id'], unique=False)
    op.create_index('ix_video_clip_marker_user_created_at', 'video_clip_marker', ['user_id', 'created_at'], unique=False)


def downgrade():
    op.drop_index('ix_video_clip_marker_user_created_at', table_name='video_clip_marker')
    op.drop_index('ix_video_clip_marker_user_video', table_name='video_clip_marker')
    op.drop_index(op.f('ix_video_clip_marker_user_id'), table_name='video_clip_marker')
    op.drop_table('video_clip_marker')
