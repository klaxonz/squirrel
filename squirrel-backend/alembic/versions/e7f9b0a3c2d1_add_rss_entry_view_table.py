"""add rss_entry_view table

Revision ID: e7f9b0a3c2d1
Revises: d4e6c8f2a1b0
Create Date: 2026-05-31 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e7f9b0a3c2d1"
down_revision = "d4e6c8f2a1b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("rss_entry_view",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("rss_entry_view_pkey")),
        sa.UniqueConstraint("user_id", "entry_id", name=op.f("uix_rss_entry_view_user_entry")),
    )
    op.create_index(op.f("ix_rss_entry_view_user_viewed"), "rss_entry_view", ["user_id", "viewed_at"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_rss_entry_view_user_viewed"), table_name="rss_entry_view")
    op.drop_table("rss_entry_view")
