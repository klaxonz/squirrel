"""add_special_follow_to_user_subscription

Revision ID: 4b1c7d8e9f02
Revises: ea8c3f9b2d41
Create Date: 2026-05-24 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = '4b1c7d8e9f02'
down_revision = 'ea8c3f9b2d41'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user_subscription',
        sa.Column('is_special_followed', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        'ix_user_subscription_user_deleted_special',
        'user_subscription',
        ['user_id', 'is_deleted', 'is_special_followed'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_user_subscription_user_deleted_special', table_name='user_subscription')
    op.drop_column('user_subscription', 'is_special_followed')
