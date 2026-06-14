"""add_video_interaction_user_type_created_index

Revision ID: b2c3d4e5f6a7
Revises: f1e2d3c4b5a6
Create Date: 2026-06-14 00:00:00.000000

Add a composite index on video_interaction (user_id, interaction_type,
created_at, id) to support keyset pagination of liked/later lists ordered
by interaction time. The existing index (user_id, interaction_type,
video_id) serves lookups but not time-ordered pagination.
"""
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_video_interaction_user_type_created",
        "video_interaction",
        ["user_id", "interaction_type", "created_at", "id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_video_interaction_user_type_created", table_name="video_interaction")
