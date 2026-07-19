import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

from sqlalchemy import Table

from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription_sync_run import SubscriptionSyncRun
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.video.domain.junctions.subscription_video import SubscriptionVideo

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / 'alembic'
    / 'versions'
    / 'd1a7c9e3f5b2_add_sync_run_and_task_fencing.py'
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location('migration_d1a7c9e3f5b2', MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _foreign_key(table: Table, column_name: str):
    foreign_keys = tuple(table.c[column_name].foreign_keys)
    assert len(foreign_keys) == 1
    return foreign_keys[0]


def test_models_declare_subscription_sync_storage_foreign_keys():
    expected = {
        (SubscriptionVideo.__table__, 'subscription_id'): (
            'subscription.id',
            'fk_subscription_video_subscription_id_subscription',
            'CASCADE',
        ),
        (SubscriptionVideo.__table__, 'video_id'): (
            'video.id',
            'fk_subscription_video_video_id_video',
            'CASCADE',
        ),
        (SubscriptionSyncState.__table__, 'subscription_id'): (
            'subscription.id',
            'fk_subscription_sync_state_subscription_id_subscription',
            'CASCADE',
        ),
        (SubscriptionSyncState.__table__, 'current_run_id'): (
            'subscription_sync_run.id',
            'fk_subscription_sync_state_current_run_id_sync_run',
            'SET NULL',
        ),
        (SubscriptionSyncRun.__table__, 'subscription_id'): (
            'subscription.id',
            'fk_subscription_sync_run_subscription_id_subscription',
            'CASCADE',
        ),
        (SubscriptionSyncRun.__table__, 'sync_state_id'): (
            'subscription_sync_state.id',
            'fk_subscription_sync_run_sync_state_id_sync_state',
            'SET NULL',
        ),
        (CrawlJob.__table__, 'subscription_id'): (
            'subscription.id',
            'fk_crawl_job_subscription_id_subscription',
            'SET NULL',
        ),
        (CrawlTask.__table__, 'subscription_id'): (
            'subscription.id',
            'fk_crawl_task_subscription_id_subscription',
            'SET NULL',
        ),
        (CrawlTask.__table__, 'sync_state_id'): (
            'subscription_sync_state.id',
            'fk_crawl_task_sync_state_id_sync_state',
            'SET NULL',
        ),
        (CrawlTask.__table__, 'run_id'): (
            'subscription_sync_run.id',
            'fk_crawl_task_run_id_sync_run',
            'SET NULL',
        ),
        (CrawlTask.__table__, 'video_id'): (
            'video.id',
            'fk_crawl_task_video_id_video',
            'SET NULL',
        ),
    }

    for (table, column_name), (target, name, ondelete) in expected.items():
        foreign_key = _foreign_key(table, column_name)
        assert foreign_key.target_fullname == target
        assert foreign_key.constraint.name == name
        assert foreign_key.ondelete == ondelete


def test_migration_trim_set_matches_python_strip_semantics():
    migration = _load_migration()
    migration_codepoints = {
        int(codepoint, 16)
        for codepoint in re.findall(r'\\([0-9A-Fa-f]{4})', migration._PYTHON_STRIP_CHARS)
    }
    python_codepoints = {codepoint for codepoint in range(sys.maxunicode + 1) if chr(codepoint).isspace()}

    assert migration_codepoints == python_codepoints


def test_migration_enforces_canonical_key_for_non_orm_writes():
    source = MIGRATION_PATH.read_text(encoding='utf-8')

    assert 'CREATE FUNCTION d1_sync_subscription_canonical_key()' in source
    assert 'BEFORE INSERT OR UPDATE OF url, canonical_key' in source
    assert 'DROP TRIGGER trg_subscription_canonical_key ON subscription' in source
    assert 'DROP FUNCTION d1_sync_subscription_canonical_key()' in source


def test_migration_is_stopped_and_rewrites_every_subscription_owner():
    source = MIGRATION_PATH.read_text(encoding='utf-8')

    assert 'stop-the-world upgrade' in source
    assert "SET LOCAL lock_timeout = '5s'" in source
    assert 'IN ACCESS EXCLUSIVE MODE' in source
    assert 'RAISE EXCEPTION' in source
    assert 'UPDATE user_subscription' in source
    assert 'INSERT INTO subscription_video' in source
    assert 'UPDATE subscription_sync_state' in source
    assert 'UPDATE crawl_job' in source
    assert 'UPDATE crawl_task' in source
    assert 'INSERT INTO subscription_sync_run' in source


def test_migration_removes_only_unrecoverable_junction_orphans_before_validation(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, 'execute', statements.append)

    migration._remove_orphan_subscription_video_links()

    cleanup_sql = statements.pop()
    assert 'DELETE FROM subscription_video sv' in cleanup_sql
    assert cleanup_sql.count('NOT EXISTS') == 2
    assert 'SELECT 1 FROM subscription s WHERE s.id = sv.subscription_id' in cleanup_sql
    assert 'OR NOT EXISTS' in cleanup_sql
    assert 'SELECT 1 FROM video v WHERE v.id = sv.video_id' in cleanup_sql
    assert 'missing subscription=%s, missing video=%s, missing both=%s' in cleanup_sql
    assert statements == []

    upgrade_source = MIGRATION_PATH.read_text(encoding='utf-8').split('def upgrade() -> None:', 1)[1]
    cleanup_position = upgrade_source.index('_remove_orphan_subscription_video_links()')
    validation_position = upgrade_source.index('_assert_existing_references_are_valid()')
    assert cleanup_position < validation_position


def test_migration_cancels_duplicate_work_before_merge_safety_validation(monkeypatch):
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, 'execute', statements.append)

    migration._cancel_duplicate_subscription_work()

    combined_sql = '\n'.join(statements)
    assert 'CREATE TEMPORARY TABLE _subscription_merge_job' in combined_sql
    assert 'CREATE TEMPORARY TABLE _subscription_merge_reschedule' in combined_sql
    assert "status = 'cancelled'" in combined_sql
    assert 'dedupe_key = NULL' in combined_sql
    assert 'ct.subscription_id = cj.subscription_id' in combined_sql
    assert "sync_status = 'idle'" in combined_sql
    assert 'pending_video_count = 0' in combined_sql
    assert 'next_sync_at = cancelled_at' in combined_sql
    assert 'summary.active_count > 0' in combined_sql
    assert "THEN 'partial_failed'" in combined_sql
    assert 'cancelled_for_subscription_merge' in combined_sql

    upgrade_source = MIGRATION_PATH.read_text(encoding='utf-8').split('def upgrade() -> None:', 1)[1]
    map_position = upgrade_source.index('_create_subscription_merge_map()')
    cancellation_position = upgrade_source.index('_cancel_duplicate_subscription_work()')
    validation_position = upgrade_source.index('_assert_subscription_merge_is_safe()')
    merge_position = upgrade_source.index('_merge_user_subscriptions()')
    assert map_position < cancellation_position < validation_position < merge_position


def test_post_merge_reference_check_scans_each_large_payload_table_once():
    source = MIGRATION_PATH.read_text(encoding='utf-8')
    check_start = source.index('WITH removed_subscription AS')
    check_end = source.index("'d1a7c9e3f5b2: a duplicate subscription still has references after merge'")
    check_sql = source[check_start:check_end]

    assert check_sql.count('FROM crawl_job cj') == 2
    assert check_sql.count('FROM crawl_task ct') == 2
    assert 'JOIN removed_subscription rs' in check_sql
    assert 'EXISTS (\n                          SELECT 1 FROM crawl_job' not in check_sql
