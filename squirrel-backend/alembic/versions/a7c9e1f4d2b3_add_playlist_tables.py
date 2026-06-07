"""add playlist tables

Revision ID: a7c9e1f4d2b3
Revises: f6a2b4c8d1e3
Create Date: 2026-04-14 22:55:00.000000

"""
import sqlalchemy as sa

from alembic import op

revision = "a7c9e1f4d2b3"
down_revision = "f6a2b4c8d1e3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "playlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=255), nullable=False),
        sa.Column("description", sa.VARCHAR(length=512), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playlist_user_created_at", "playlist", ["user_id", "created_at"], unique=False)
    op.create_index("ix_playlist_user_name", "playlist", ["user_id", "name"], unique=False)

    op.create_table(
        "playlist_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("playlist_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playlist_item_playlist_position", "playlist_item", ["playlist_id", "position"], unique=False)
    op.create_index("ix_playlist_item_user_video", "playlist_item", ["user_id", "video_id"], unique=False)


def downgrade():
    op.drop_index("ix_playlist_item_user_video", table_name="playlist_item")
    op.drop_index("ix_playlist_item_playlist_position", table_name="playlist_item")
    op.drop_table("playlist_item")

    op.drop_index("ix_playlist_user_name", table_name="playlist")
    op.drop_index("ix_playlist_user_created_at", table_name="playlist")
    op.drop_table("playlist")
