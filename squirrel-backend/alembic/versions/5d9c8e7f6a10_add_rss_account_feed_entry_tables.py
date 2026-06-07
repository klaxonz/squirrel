"""add rss account feed entry tables

Revision ID: 5d9c8e7f6a10
Revises: 4b1c7d8e9f02
Create Date: 2026-05-30 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5d9c8e7f6a10"
down_revision: str | None = "4b1c7d8e9f02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rss_account",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=32), nullable=False),
        sa.Column("name", sa.VARCHAR(length=120), nullable=False),
        sa.Column("base_url", sa.VARCHAR(length=2048), nullable=False),
        sa.Column("username", sa.VARCHAR(length=255), nullable=True),
        sa.Column("credential_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", "base_url", "name", name="uix_rss_account_user_provider_url_name"),
    )
    op.create_index("ix_rss_account_user_provider", "rss_account", ["user_id", "provider"])

    op.create_table(
        "rss_feed",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("external_feed_id", sa.VARCHAR(length=255), nullable=False),
        sa.Column("title", sa.VARCHAR(length=512), nullable=False),
        sa.Column("feed_url", sa.VARCHAR(length=2048), nullable=True),
        sa.Column("site_url", sa.VARCHAR(length=2048), nullable=True),
        sa.Column("icon_url", sa.VARCHAR(length=2048), nullable=True),
        sa.Column("category", sa.VARCHAR(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("last_entry_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "external_feed_id", name="uix_rss_feed_account_external"),
    )
    op.create_index("ix_rss_feed_account_enabled", "rss_feed", ["account_id", "enabled"])
    op.create_index("ix_rss_feed_user_title", "rss_feed", ["user_id", "title"])

    op.create_table(
        "rss_entry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("external_entry_id", sa.VARCHAR(length=255), nullable=False),
        sa.Column("canonical_url", sa.VARCHAR(length=2048), nullable=False),
        sa.Column("title", sa.VARCHAR(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("thumbnail", sa.VARCHAR(length=2048), nullable=True),
        sa.Column("author", sa.VARCHAR(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("is_starred", sa.Boolean(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feed_id", "external_entry_id", name="uix_rss_entry_feed_external"),
    )
    op.create_index("ix_rss_entry_feed_published", "rss_entry", ["feed_id", "published_at"])
    op.create_index("ix_rss_entry_user_published", "rss_entry", ["user_id", "published_at"])
    op.create_index("ix_rss_entry_user_read", "rss_entry", ["user_id", "is_read", "published_at"])

    op.create_table(
        "rss_entry_media",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("media_url", sa.VARCHAR(length=2048), nullable=False),
        sa.Column("media_type", sa.VARCHAR(length=120), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("video_id", sa.Integer(), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "media_url", name="uix_rss_entry_media_entry_url"),
    )
    op.create_index("ix_rss_entry_media_entry", "rss_entry_media", ["entry_id"])
    op.create_index("ix_rss_entry_media_video", "rss_entry_media", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_rss_entry_media_video", table_name="rss_entry_media")
    op.drop_index("ix_rss_entry_media_entry", table_name="rss_entry_media")
    op.drop_table("rss_entry_media")
    op.drop_index("ix_rss_entry_user_read", table_name="rss_entry")
    op.drop_index("ix_rss_entry_user_published", table_name="rss_entry")
    op.drop_index("ix_rss_entry_feed_published", table_name="rss_entry")
    op.drop_table("rss_entry")
    op.drop_index("ix_rss_feed_user_title", table_name="rss_feed")
    op.drop_index("ix_rss_feed_account_enabled", table_name="rss_feed")
    op.drop_table("rss_feed")
    op.drop_index("ix_rss_account_user_provider", table_name="rss_account")
    op.drop_table("rss_account")
