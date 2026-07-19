"""add cascading foreign keys to the RSS ownership graph

Revision ID: e2b4c6d8f0a1
Revises: d1a7c9e3f5b2
Create Date: 2026-07-20

RSS tables historically relied on application-side cleanup. That leaves a
race where a concurrent writer can recreate a child after its parent account
has been deleted. This migration removes legacy orphan rows and makes the
database enforce the four strong ownership relationships.

The migration locks the complete RSS graph before cleanup so a live writer
cannot insert a new orphan between cleanup and ``ADD CONSTRAINT``. Each
constraint is inspected before creation, making a partially applied migration
auditable and safe to rerun.
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e2b4c6d8f0a1'
down_revision: str | None = 'd1a7c9e3f5b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = logging.getLogger('alembic.e2b4c6d8f0a1')

# Keep parent-first order: deleting an orphan feed may create orphan entries,
# and deleting orphan entries may create orphan entry-view rows.
_FK_SPECS = (
    ('fk_rss_feed_account_id_rss_account', 'rss_feed', 'account_id', 'rss_account'),
    ('fk_rss_entry_account_id_rss_account', 'rss_entry', 'account_id', 'rss_account'),
    ('fk_rss_entry_feed_id_rss_feed', 'rss_entry', 'feed_id', 'rss_feed'),
    ('fk_rss_entry_view_entry_id_rss_entry', 'rss_entry_view', 'entry_id', 'rss_entry'),
)


def _matching_foreign_key(bind, source_table: str, local_column: str, parent_table: str):
    return next(
        (
            foreign_key
            for foreign_key in sa.inspect(bind).get_foreign_keys(source_table)
            if foreign_key['referred_table'] == parent_table
            and tuple(foreign_key['constrained_columns']) == (local_column,)
        ),
        None,
    )


def upgrade() -> None:
    bind = op.get_bind()
    op.execute('LOCK TABLE rss_account, rss_feed, rss_entry, rss_entry_view IN SHARE ROW EXCLUSIVE MODE')

    for constraint_name, source_table, local_column, parent_table in _FK_SPECS:
        existing = _matching_foreign_key(bind, source_table, local_column, parent_table)
        if existing:
            ondelete = str((existing.get('options') or {}).get('ondelete') or '').upper()
            if ondelete != 'CASCADE':
                raise RuntimeError(
                    f'{source_table}.{local_column} already has a non-cascading foreign key '
                    f'{existing.get("name")!r}; refusing to silently replace it'
                )
            log.info(
                'Skipping %s: cascading FK already exists on %s(%s)',
                constraint_name,
                source_table,
                local_column,
            )
            continue

        result = bind.execute(
            sa.text(
                f'DELETE FROM {source_table} AS child '
                f'WHERE NOT EXISTS ('
                f'SELECT 1 FROM {parent_table} AS parent '
                f'WHERE parent.id = child.{local_column}'
                f')'
            )
        )
        if result.rowcount and result.rowcount > 0:
            log.warning(
                'Removed %d orphan row(s) from %s.%s before adding %s',
                result.rowcount,
                source_table,
                local_column,
                constraint_name,
            )

        op.create_foreign_key(
            constraint_name,
            source_table,
            parent_table,
            [local_column],
            ['id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    bind = op.get_bind()
    for constraint_name, source_table, _local_column, _parent_table in reversed(_FK_SPECS):
        existing_names = {foreign_key['name'] for foreign_key in sa.inspect(bind).get_foreign_keys(source_table)}
        if constraint_name in existing_names:
            op.drop_constraint(constraint_name, source_table, type_='foreignkey')
