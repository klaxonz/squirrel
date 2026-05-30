"""add rss account sync entry limit

Revision ID: 8f6a2d91c0e4
Revises: 7c41a96d2e58
Create Date: 2026-05-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8f6a2d91c0e4'
down_revision: Union[str, None] = '7c41a96d2e58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rss_account', sa.Column('sync_entry_limit', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('rss_account', 'sync_entry_limit')
