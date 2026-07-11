"""cleanup video interaction orphans

Revision ID: f3a9d6c1b8e2
Revises: a4d9b6e2c731
Create Date: 2026-07-11 00:00:00.000000

Remove interaction rows pointing at hard-deleted videos and enforce the video
foreign key. Liked/later rows are user-owned state and should survive
subscription changes, but they cannot represent a playable item when the video
row itself is gone.
"""

import sqlalchemy as sa

from alembic import op

revision = 'f3a9d6c1b8e2'
down_revision = 'a4d9b6e2c731'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            'DELETE FROM video_interaction '
            'WHERE video_id NOT IN (SELECT id FROM video)'
        )
    )

    inspector = sa.inspect(bind)
    existing_fks = {
        (fk['referred_table'], tuple(fk['constrained_columns']))
        for fk in inspector.get_foreign_keys('video_interaction')
    }
    if ('video', ('video_id',)) not in existing_fks:
        op.create_foreign_key(
            'fk_video_interaction_video_id_video',
            'video_interaction',
            'video',
            ['video_id'],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade():
    op.drop_constraint('fk_video_interaction_video_id_video', 'video_interaction', type_='foreignkey')
