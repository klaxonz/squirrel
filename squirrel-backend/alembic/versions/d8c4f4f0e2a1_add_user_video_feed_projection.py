"""add user video feed projection

Revision ID: d8c4f4f0e2a1
Revises: c8d5ef1a4b2c
Create Date: 2026-03-28 19:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd8c4f4f0e2a1'
down_revision = 'c8d5ef1a4b2c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_video_feed',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('publish_date', sa.DateTime(), nullable=True),
        sa.Column('video_created_at', sa.DateTime(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('is_nsfw', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'subscription_id', 'video_id', name='uix_user_video_feed_user_sub_video'),
    )
    op.create_index('ix_user_video_feed_user_publish_video', 'user_video_feed', ['user_id', 'publish_date', 'video_id'], unique=False)
    op.create_index('ix_user_video_feed_user_created_video', 'user_video_feed', ['user_id', 'video_created_at', 'video_id'], unique=False)
    op.create_index('ix_user_video_feed_user_sub_publish', 'user_video_feed', ['user_id', 'subscription_id', 'publish_date'], unique=False)
    op.create_index('ix_user_video_feed_user_nsfw_publish', 'user_video_feed', ['user_id', 'is_nsfw', 'publish_date'], unique=False)
    op.create_index('ix_user_video_feed_video_id', 'user_video_feed', ['video_id'], unique=False)

    op.execute("""
        INSERT INTO user_video_feed (
            user_id,
            subscription_id,
            video_id,
            publish_date,
            video_created_at,
            domain,
            is_nsfw,
            created_at,
            updated_at
        )
        SELECT
            us.user_id,
            sv.subscription_id,
            sv.video_id,
            v.publish_date,
            v.created_at,
            v.domain,
            us.is_nsfw,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM user_subscription us
        JOIN subscription s ON s.id = us.subscription_id
        JOIN subscription_video sv ON sv.subscription_id = us.subscription_id
        JOIN video v ON v.id = sv.video_id
        WHERE us.is_deleted = FALSE
          AND s.is_deleted = FALSE
          AND v.is_deleted = FALSE
    """)


def downgrade():
    op.drop_index('ix_user_video_feed_video_id', table_name='user_video_feed')
    op.drop_index('ix_user_video_feed_user_nsfw_publish', table_name='user_video_feed')
    op.drop_index('ix_user_video_feed_user_sub_publish', table_name='user_video_feed')
    op.drop_index('ix_user_video_feed_user_created_video', table_name='user_video_feed')
    op.drop_index('ix_user_video_feed_user_publish_video', table_name='user_video_feed')
    op.drop_table('user_video_feed')
