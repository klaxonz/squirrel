"""rename_vip_video_record_to_blocked_video_record

Revision ID: c4a7d1e2f9b3
Revises: d8c4f4f0e2a1
Create Date: 2026-03-29 21:45:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "c4a7d1e2f9b3"
down_revision = "d8c4f4f0e2a1"
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("vip_video_record", "blocked_video_record")
    op.execute("ALTER INDEX ux_vip_video_url_unique RENAME TO ux_blocked_video_url_unique")
    op.execute("ALTER INDEX ix_vip_video_url RENAME TO ix_blocked_video_url")
    op.execute("ALTER INDEX ix_vip_video_site RENAME TO ix_blocked_video_site")
    op.execute("ALTER INDEX ix_vip_video_created_at RENAME TO ix_blocked_video_created_at")
    op.add_column("blocked_video_record", sa.Column("reason_code", sa.VARCHAR(length=128), nullable=True))
    op.execute("UPDATE blocked_video_record SET reason_code = 'vip_required' WHERE reason_code IS NULL")
    op.alter_column("blocked_video_record", "reason_code", existing_type=sa.VARCHAR(length=128), nullable=False)
    op.create_index("ix_blocked_video_reason_code", "blocked_video_record", ["reason_code"], unique=False)


def downgrade():
    op.drop_index("ix_blocked_video_reason_code", table_name="blocked_video_record")
    op.drop_column("blocked_video_record", "reason_code")
    op.execute("ALTER INDEX ux_blocked_video_url_unique RENAME TO ux_vip_video_url_unique")
    op.execute("ALTER INDEX ix_blocked_video_url RENAME TO ix_vip_video_url")
    op.execute("ALTER INDEX ix_blocked_video_site RENAME TO ix_vip_video_site")
    op.execute("ALTER INDEX ix_blocked_video_created_at RENAME TO ix_vip_video_created_at")
    op.rename_table("blocked_video_record", "vip_video_record")
