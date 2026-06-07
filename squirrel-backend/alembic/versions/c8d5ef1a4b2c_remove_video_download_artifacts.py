"""remove video download artifacts

Revision ID: c8d5ef1a4b2c
Revises: b3f6b4e5c1aa
Create Date: 2026-03-28 13:45:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d5ef1a4b2c"
down_revision = "b3f6b4e5c1aa"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "download_task" in inspector.get_table_names():
        op.drop_table("download_task")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "download_task" not in inspector.get_table_names():
        op.create_table(
            "download_task",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("video_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("downloaded_size", sa.BigInteger(), nullable=True),
            sa.Column("total_size", sa.BigInteger(), nullable=True),
            sa.Column("speed", sa.String(length=255), nullable=True),
            sa.Column("eta", sa.String(length=32), nullable=True),
            sa.Column("percent", sa.String(length=32), nullable=True),
            sa.Column("retry", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
