"""add preview image url to video clip marker

Revision ID: 1d4b7f2c8a9e
Revises: a7c9e1f4d2b3
Create Date: 2026-04-14 23:50:00
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1d4b7f2c8a9e"
down_revision = "a7c9e1f4d2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("video_clip_marker", sa.Column("preview_image_url", sa.VARCHAR(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("video_clip_marker", "preview_image_url")
