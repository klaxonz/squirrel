"""delete table channel and channel_video

Revision ID: 4d7591a3502c
Revises: f17f5d39b5ef
Create Date: 2024-12-22 19:04:04.377353

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4d7591a3502c'
down_revision = 'f17f5d39b5ef'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_channel_name', table_name='channel')
    op.drop_index('ix_channel_channel_id', table_name='channel')
    op.drop_index('ix_channel_created_at', table_name='channel')
    op.drop_index('ix_channel_updated_at', table_name='channel')
    op.drop_table('channel')
    op.drop_index('idx_channel_video_channel_uploaded', table_name='channel_video')
    op.drop_index('idx_channel_video_read_status', table_name='channel_video')
    op.drop_index('ix_channel_video_channel_id', table_name='channel_video')
    op.drop_index('ix_channel_video_updated_at', table_name='channel_video')
    op.drop_index('ix_channel_video_uploaded_at', table_name='channel_video')
    op.drop_index('ix_channel_video_video_id', table_name='channel_video')
    op.drop_table('channel_video')
    op.drop_column('download_task', 'channel_url')
    op.drop_column('download_task', 'channel_avatar')
    op.drop_column('download_task', 'channel_id')
    op.drop_column('download_task', 'title')
    op.drop_column('download_task', 'domain')
    op.drop_column('download_task', 'channel_name')
    op.drop_column('download_task', 'thumbnail')
    op.drop_column('download_task', 'url')
    op.alter_column('video_history', 'video_id',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255),
               type_=sa.Integer(),
               existing_nullable=False)
    op.drop_column('video_history', 'channel_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('video_history', sa.Column('channel_id', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False))
    op.alter_column('video_history', 'video_id',
               existing_type=sa.Integer(),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255),
               existing_nullable=False)
    op.add_column('download_task', sa.Column('url', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=2048), nullable=False))
    op.add_column('download_task', sa.Column('thumbnail', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=2048), nullable=True))
    op.add_column('download_task', sa.Column('channel_name', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=True))
    op.add_column('download_task', sa.Column('domain', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False))
    op.add_column('download_task', sa.Column('title', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=True))
    op.add_column('download_task', sa.Column('channel_id', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=True))
    op.add_column('download_task', sa.Column('channel_avatar', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=2048), nullable=True))
    op.add_column('download_task', sa.Column('channel_url', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=2048), nullable=True))
    op.create_table('channel_video',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('channel_id', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False),
    sa.Column('channel_name', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False),
    sa.Column('channel_avatar', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=2048), nullable=False),
    sa.Column('title', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1024), nullable=True),
    sa.Column('video_id', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=64), nullable=False),
    sa.Column('domain', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False),
    sa.Column('url', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1024), nullable=False),
    sa.Column('thumbnail', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=2048), nullable=True),
    sa.Column('duration', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('if_read', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('if_downloaded', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('uploaded_at', mysql.DATETIME(), nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=False),
    sa.Column('updated_at', mysql.DATETIME(), nullable=False),
    sa.Column('is_liked', mysql.INTEGER(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_channel_video_video_id', 'channel_video', ['video_id'], unique=False)
    op.create_index('ix_channel_video_uploaded_at', 'channel_video', ['uploaded_at'], unique=False)
    op.create_index('ix_channel_video_updated_at', 'channel_video', ['updated_at'], unique=False)
    op.create_index('ix_channel_video_channel_id', 'channel_video', ['channel_id'], unique=False)
    op.create_index('idx_channel_video_read_status', 'channel_video', ['channel_id', 'if_read'], unique=False)
    op.create_index('idx_channel_video_channel_uploaded', 'channel_video', ['channel_id', 'uploaded_at'], unique=False)
    op.create_table('channel',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('channel_id', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False),
    sa.Column('name', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=255), nullable=False),
    sa.Column('url', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=1024), nullable=False),
    sa.Column('avatar', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=2048), nullable=False),
    sa.Column('total_videos', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('if_enable', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('if_auto_download', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('if_download_all', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('if_extract_all', mysql.TINYINT(display_width=1), autoincrement=False, nullable=True),
    sa.Column('created_at', mysql.DATETIME(), nullable=False),
    sa.Column('updated_at', mysql.DATETIME(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_unicode_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_index('ix_channel_updated_at', 'channel', ['updated_at'], unique=False)
    op.create_index('ix_channel_created_at', 'channel', ['created_at'], unique=False)
    op.create_index('ix_channel_channel_id', 'channel', ['channel_id'], unique=False)
    op.create_index('idx_channel_name', 'channel', ['name'], unique=False)
    # ### end Alembic commands ###
