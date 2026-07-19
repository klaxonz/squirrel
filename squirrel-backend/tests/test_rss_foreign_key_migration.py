import importlib.util
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / 'alembic' / 'versions' / 'e2b4c6d8f0a1_add_rss_cascade_foreign_keys.py'
)


def _load_migration():
    spec = importlib.util.spec_from_file_location('rss_foreign_key_migration', MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rss_foreign_key_migration_cleans_orphans_then_adds_cascades(monkeypatch):
    migration = _load_migration()
    executed_sql = []
    created_foreign_keys = []

    class _Result:
        rowcount = 0

    class _Bind:
        def execute(self, statement):
            executed_sql.append(str(statement))
            return _Result()

    class _Inspector:
        def get_foreign_keys(self, table_name):
            return []

    class _Op:
        def __init__(self):
            self.bind = _Bind()

        def get_bind(self):
            return self.bind

        def execute(self, statement):
            executed_sql.append(str(statement))

        def create_foreign_key(self, *args, **kwargs):
            created_foreign_keys.append((args, kwargs))

    monkeypatch.setattr(migration, 'op', _Op())
    monkeypatch.setattr(migration.sa, 'inspect', lambda bind: _Inspector())

    migration.upgrade()

    assert migration.down_revision == 'd1a7c9e3f5b2'
    assert executed_sql[0].startswith('LOCK TABLE rss_account, rss_feed, rss_entry, rss_entry_view')
    assert [sql.split(' AS child', 1)[0] for sql in executed_sql[1:]] == [
        'DELETE FROM rss_feed',
        'DELETE FROM rss_entry',
        'DELETE FROM rss_entry',
        'DELETE FROM rss_entry_view',
    ]
    assert [args[0] for args, _kwargs in created_foreign_keys] == [
        'fk_rss_feed_account_id_rss_account',
        'fk_rss_entry_account_id_rss_account',
        'fk_rss_entry_feed_id_rss_feed',
        'fk_rss_entry_view_entry_id_rss_entry',
    ]
    assert all(kwargs == {'ondelete': 'CASCADE'} for _args, kwargs in created_foreign_keys)
