"""add user video feed domain index

Revision ID: ea8c3f9b2d41
Revises: c9a1f3e7d5b2
Create Date: 2026-05-24 02:30:00.000000

"""
from alembic import op


revision = 'ea8c3f9b2d41'
down_revision = 'c9a1f3e7d5b2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'ix_user_video_feed_user_domain_publish_video',
        'user_video_feed',
        ['user_id', 'domain', 'publish_date', 'video_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_user_video_feed_user_domain_publish_video', table_name='user_video_feed')
