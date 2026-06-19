"""dedupe video history and add unique index

Revision ID: b3f6b4e5c1aa
Revises: f2c4b6a8d001
Create Date: 2026-03-27 17:40:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b3f6b4e5c1aa'
down_revision = 'f2c4b6a8d001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        WITH ranked_history AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id, video_id
                    ORDER BY end_time DESC, id DESC
                ) AS row_num
            FROM video_history
        )
        DELETE FROM video_history
        WHERE id IN (
            SELECT id
            FROM ranked_history
            WHERE row_num > 1
        )
        """,
    )
    op.drop_index('ix_video_history_user_video', table_name='video_history')
    op.create_index('ux_video_history_user_video', 'video_history', ['user_id', 'video_id'], unique=True)


def downgrade():
    op.drop_index('ux_video_history_user_video', table_name='video_history')
    op.create_index('ix_video_history_user_video', 'video_history', ['user_id', 'video_id'], unique=False)
