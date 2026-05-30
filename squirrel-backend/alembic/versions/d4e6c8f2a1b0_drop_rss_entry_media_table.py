"""drop rss_entry_media table

Revision ID: d4e6c8f2a1b0
Revises: b1e3c5d7f908
Create Date: 2026-05-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd4e6c8f2a1b0'
down_revision = 'b1e3c5d7f908'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index(op.f('ix_rss_entry_media_entry'), table_name='rss_entry_media')
    op.drop_index(op.f('ix_rss_entry_media_video'), table_name='rss_entry_media')
    op.drop_table('rss_entry_media')


def downgrade():
    op.create_table('rss_entry_media',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('account_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('feed_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('entry_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('media_url', sa.VARCHAR(length=2048), autoincrement=False, nullable=False),
        sa.Column('media_type', sa.VARCHAR(length=120), autoincrement=False, nullable=True),
        sa.Column('duration', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('video_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('raw_data', postgresql.JSON(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('rss_entry_media_pkey')),
        sa.UniqueConstraint('entry_id', 'media_url', name=op.f('uix_rss_entry_media_entry_url')),
    )
    op.create_index(op.f('ix_rss_entry_media_entry'), 'rss_entry_media', ['entry_id'], unique=False)
    op.create_index(op.f('ix_rss_entry_media_video'), 'rss_entry_media', ['video_id'], unique=False)
