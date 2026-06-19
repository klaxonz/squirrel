"""add user token version

Revision ID: e4f2a6b1c9d0
Revises: c2f8a1d4b6e7
Create Date: 2026-04-10 02:20:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = 'e4f2a6b1c9d0'
down_revision = 'c2f8a1d4b6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade():
    op.drop_column('user', 'token_version')
