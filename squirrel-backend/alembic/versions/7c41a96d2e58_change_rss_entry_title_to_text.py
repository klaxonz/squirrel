"""change rss entry title to text

Revision ID: 7c41a96d2e58
Revises: 5d9c8e7f6a10
Create Date: 2026-05-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '7c41a96d2e58'
down_revision: str | None = '5d9c8e7f6a10'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        'rss_entry',
        'title',
        existing_type=sa.VARCHAR(length=512),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'rss_entry',
        'title',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=512),
        existing_nullable=False,
    )
