"""add podcast play history

Revision ID: 43d8096de989
Revises: 2561b394bb3d
Create Date: 2024-12-01 15:17:24.919079

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '43d8096de989'
down_revision = '2561b394bb3d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('podcast_play_history',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('episode_id', sa.Integer(), nullable=False),
                    sa.Column('position', sa.Integer(), nullable=False),
                    sa.Column('duration', sa.Integer(), nullable=False),
                    sa.Column('last_played_at', sa.DateTime(), nullable=False),
                    sa.Column('is_finished', sa.Boolean(), nullable=False),
                    sa.ForeignKeyConstraint(['episode_id'], ['podcast_episodes.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('podcast_play_history')
    # ### end Alembic commands ###
