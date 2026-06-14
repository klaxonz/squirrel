"""drop_user_video_feed

Revision ID: f1e2d3c4b5a6
Revises: d3b72f9a4c61
Create Date: 2026-06-14 00:00:00.000000

Remove the user_video_feed projection table. Search now goes through
Meilisearch (text + structural recall); permission/category filtering
uses a real-time join over UserSubscription x SubscriptionVideo x Video.
"""
import sqlalchemy as sa

from alembic import op

revision = "f1e2d3c4b5a6"
down_revision = "d3b72f9a4c61"
branch_labels = None
depends_on = None


def upgrade():
    # Drop indexes first (all 6, including the domain index from ea8c3f9b2d41)
    op.drop_index("ix_user_video_feed_user_domain_publish_video", table_name="user_video_feed")
    op.drop_index("ix_user_video_feed_video_id", table_name="user_video_feed")
    op.drop_index("ix_user_video_feed_user_nsfw_publish", table_name="user_video_feed")
    op.drop_index("ix_user_video_feed_user_sub_publish", table_name="user_video_feed")
    op.drop_index("ix_user_video_feed_user_created_video", table_name="user_video_feed")
    op.drop_index("ix_user_video_feed_user_publish_video", table_name="user_video_feed")
    op.drop_table("user_video_feed")


def downgrade():
    # Rebuild the projection table and backfill from junctions (mirrors
    # the original creation in d8c4f4f0e2a1 + domain index from ea8c3f9b2d41).
    op.create_table(
        "user_video_feed",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("publish_date", sa.DateTime(), nullable=True),
        sa.Column("video_created_at", sa.DateTime(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("is_nsfw", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint(
            "user_id", "subscription_id", "video_id",
            name="uix_user_video_feed_user_sub_video",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_video_feed_user_publish_video", "user_video_feed", ["user_id", "publish_date", "video_id"], unique=False)
    op.create_index("ix_user_video_feed_user_created_video", "user_video_feed", ["user_id", "video_created_at", "video_id"], unique=False)
    op.create_index("ix_user_video_feed_user_sub_publish", "user_video_feed", ["user_id", "subscription_id", "publish_date"], unique=False)
    op.create_index("ix_user_video_feed_user_nsfw_publish", "user_video_feed", ["user_id", "is_nsfw", "publish_date"], unique=False)
    op.create_index("ix_user_video_feed_video_id", "user_video_feed", ["video_id"], unique=False)
    op.create_index("ix_user_video_feed_user_domain_publish_video", "user_video_feed", ["user_id", "domain", "publish_date", "video_id"], unique=False)

    op.execute("""
        INSERT INTO user_video_feed (user_id, subscription_id, video_id, publish_date, video_created_at, domain, is_nsfw, created_at, updated_at)
        SELECT
            us.user_id,
            sv.subscription_id,
            sv.video_id,
            v.publish_date,
            v.created_at AS video_created_at,
            v.domain,
            us.is_nsfw,
            NOW(),
            NOW()
        FROM user_subscription us
        JOIN subscription s ON s.id = us.subscription_id
        JOIN subscription_video sv ON sv.subscription_id = us.subscription_id
        JOIN video v ON v.id = sv.video_id
        WHERE us.is_deleted = FALSE
          AND s.is_deleted = FALSE
          AND v.is_deleted = FALSE
    """)
