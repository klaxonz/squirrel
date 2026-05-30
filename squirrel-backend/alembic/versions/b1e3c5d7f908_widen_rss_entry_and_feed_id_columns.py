"""widen rss entry and feed id columns

Revision ID: b1e3c5d7f908
Revises: 8f6a2d91c0e4
Create Date: 2026-05-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1e3c5d7f908'
down_revision: Union[str, None] = '8f6a2d91c0e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'rss_entry',
        'external_entry_id',
        existing_type=sa.VARCHAR(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        'rss_entry',
        'author',
        existing_type=sa.VARCHAR(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        'rss_feed',
        'external_feed_id',
        existing_type=sa.VARCHAR(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'rss_entry',
        'external_entry_id',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        'rss_entry',
        'author',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        'rss_feed',
        'external_feed_id',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=False,
    )
