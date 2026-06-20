"""add foreign key constraints for key cross-table references

Revision ID: e9a1f3c7d4b8
Revises: f6c4027dbf73
Create Date: 2026-06-20 12:00:00.000000

Adds ON DELETE CASCADE foreign keys for the strongest ownership relationships:

  account.user_id          -> user.id
  user_config.user_id      -> user.id
  user_subscription.user_id           -> user.id
  user_subscription.subscription_id   -> subscription.id
  playlist_item.playlist_id -> playlist.id
  playlist_item.user_id     -> user.id
  playlist_item.video_id    -> video.id
  video_clip_marker.user_id  -> user.id
  video_clip_marker.video_id -> video.id

Why CASCADE: these are all strong dependents -- deleting the parent row should
not leave orphan children. Cascade makes that the database's responsibility
instead of relying on every delete path to remember to clean up children.

NOT included: ``task_execution_log.task_id``. That table is an append-only
audit log; the target database already holds ~285k historical log rows whose
task has since been hard-deleted. Those rows are valuable audit history, not
garbage to be cascade-removed, so we deliberately do NOT enforce a FK there.
The model declaration also omits the FK for the same reason.

Data integrity (self-contained migration):
------------------------------------------
Because the schema historically had no FK enforcement, child rows may exist
whose foreign key points at a parent row that was hard-deleted (not soft-
deleted) by an earlier migration or manual operation. ``ADD CONSTRAINT``
would fail on such orphans, so this migration deletes orphan children *before*
adding each constraint. The deletion is logged so operators can audit the
blast radius in the migration output.

Each FK is also made idempotent: if the constraint already exists (e.g. from a
partial earlier run), it is skipped.

NOTE on the ``user`` table: it is a reserved word in PostgreSQL, so every
reference is double-quoted to ensure the table (not the CURRENT_USER alias) is
read during orphan cleanup.
"""

import logging

import sqlalchemy as sa

from alembic import op

log = logging.getLogger('alembic.e9a1f3c7d4b8')

revision = 'e9a1f3c7d4b8'
down_revision = 'f6c4027dbf73'
branch_labels = None
depends_on = None


# (constraint_name, source_table, local_column, referenced_table, referenced_column)
# `ref_table` is rendered verbatim into SQL, so reserved words like "user" are
# already quoted here.
_FK_SPECS = [
    ('fk_account_user_id_user', 'account', 'user_id', '"user"', 'id'),
    ('fk_user_config_user_id_user', 'user_config', 'user_id', '"user"', 'id'),
    ('fk_user_subscription_user_id_user', 'user_subscription', 'user_id', '"user"', 'id'),
    ('fk_user_subscription_subscription_id_subscription', 'user_subscription', 'subscription_id', 'subscription', 'id'),
    ('fk_playlist_item_playlist_id_playlist', 'playlist_item', 'playlist_id', 'playlist', 'id'),
    ('fk_playlist_item_user_id_user', 'playlist_item', 'user_id', '"user"', 'id'),
    ('fk_playlist_item_video_id_video', 'playlist_item', 'video_id', 'video', 'id'),
    ('fk_video_clip_marker_user_id_user', 'video_clip_marker', 'user_id', '"user"', 'id'),
    ('fk_video_clip_marker_video_id_video', 'video_clip_marker', 'video_id', 'video', 'id'),
]


def _orphan_delete_sql(source_table: str, local_col: str, ref_table: str) -> str:
    return (
        f'DELETE FROM {source_table} '
        f'WHERE {local_col} NOT IN (SELECT id FROM {ref_table})'
    )


def upgrade():
    bind = op.get_bind()

    for name, source_table, local_col, ref_table, ref_col in _FK_SPECS:
        inspector = sa.inspect(bind)
        existing_fks = {
            (fk['referred_table'], tuple(fk['constrained_columns']))
            for fk in inspector.get_foreign_keys(source_table)
        }
        # Inspector normalizes the table name to ``user`` (no quotes) for matching.
        ref_table_unquoted = ref_table.strip('"')
        if (ref_table_unquoted, (local_col,)) in existing_fks:
            log.info('Skipping %s: FK already exists on %s(%s)', name, source_table, local_col)
            continue

        # Remove orphan child rows BEFORE adding the constraint, otherwise
        # ADD CONSTRAINT fails on databases that accumulated orphans while FK
        # enforcement was absent. Only deletes rows pointing at parents that
        # truly do not exist (hard-deleted); soft-deleted parents are still
        # present in the table and are NOT considered orphans.
        delete_sql = _orphan_delete_sql(source_table, local_col, ref_table)
        result = bind.execute(sa.text(delete_sql))
        if result.rowcount:
            log.warning(
                'Removed %d orphan row(s) from %s.%s (no matching %s.id) before adding FK %s',
                result.rowcount, source_table, local_col, ref_table_unquoted, name,
            )

        op.create_foreign_key(
            name,
            source_table,
            ref_table_unquoted,
            [local_col],
            [ref_col],
            ondelete='CASCADE',
        )


def downgrade():
    for name, source_table, _local_col, _ref_table, _ref_col in _FK_SPECS:
        op.drop_constraint(name, source_table, type_='foreignkey')
