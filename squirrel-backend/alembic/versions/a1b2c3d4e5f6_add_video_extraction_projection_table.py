"""add_video_extraction_projection_table

Revision ID: a1b2c3d4e5f6
Revises: 9f1c2d3e4b5a
Create Date: 2026-04-05 00:30:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "9f1c2d3e4b5a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "video_extraction_projection",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("group_kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("group_value", sa.VARCHAR(length=64), nullable=False),
        sa.Column("site", sa.VARCHAR(length=64), nullable=True),
        sa.Column("sync_status", sa.VARCHAR(length=16), nullable=False, server_default="idle"),
        sa.Column("display_status", sa.VARCHAR(length=16), nullable=False, server_default="healthy"),
        sa.Column("current_phase", sa.VARCHAR(length=32), nullable=True),
        sa.Column("last_error", sa.TEXT(), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("pending_video_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batch_task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("running_task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_task_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subscription_id",
            "group_kind",
            "group_value",
            name="uix_video_extraction_projection_group",
        ),
    )
    op.create_index(
        "ix_video_extraction_projection_subscription_id",
        "video_extraction_projection",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_video_extraction_projection_display_status",
        "video_extraction_projection",
        ["display_status"],
        unique=False,
    )
    op.create_index(
        "ix_video_extraction_projection_updated_at",
        "video_extraction_projection",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_video_extraction_projection_status_updated",
        "video_extraction_projection",
        ["display_status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_video_extraction_projection_status_queued_at",
        "video_extraction_projection",
        ["display_status", "queued_at"],
        unique=False,
    )
    op.create_index(
        "ix_video_extraction_projection_status_locked_at",
        "video_extraction_projection",
        ["display_status", "locked_at"],
        unique=False,
    )

    op.create_index(
        "ix_crawl_task_subscription_id",
        "crawl_task",
        ["subscription_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_crawl_task_subscription_id", table_name="crawl_task")

    op.drop_index(
        "ix_video_extraction_projection_status_locked_at",
        table_name="video_extraction_projection",
    )
    op.drop_index(
        "ix_video_extraction_projection_status_queued_at",
        table_name="video_extraction_projection",
    )
    op.drop_index(
        "ix_video_extraction_projection_status_updated",
        table_name="video_extraction_projection",
    )
    op.drop_index(
        "ix_video_extraction_projection_updated_at",
        table_name="video_extraction_projection",
    )
    op.drop_index(
        "ix_video_extraction_projection_display_status",
        table_name="video_extraction_projection",
    )
    op.drop_index(
        "ix_video_extraction_projection_subscription_id",
        table_name="video_extraction_projection",
    )
    op.drop_table("video_extraction_projection")
