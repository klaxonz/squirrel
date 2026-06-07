"""add rss_feed.open_method column

Revision ID: f8a2b7c9d0e1
Revises: e7f9b0a3c2d1
Create Date: 2026-05-31 11:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f8a2b7c9d0e1"
down_revision = "e7f9b0a3c2d1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rss_feed", sa.Column("open_method", sa.VARCHAR(32), nullable=True))


def downgrade():
    op.drop_column("rss_feed", "open_method")
