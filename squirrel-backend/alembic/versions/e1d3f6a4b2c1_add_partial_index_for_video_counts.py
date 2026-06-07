"""add partial index for video counts

Revision ID: e1d3f6a4b2c1
Revises: 662a2b1c9d44
Create Date: 2026-03-21 10:20:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e1d3f6a4b2c1"
down_revision = "662a2b1c9d44"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_video_active_id_publish_date",
        "video",
        ["id", "publish_date"],
        unique=False,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade():
    op.drop_index("ix_video_active_id_publish_date", table_name="video")
