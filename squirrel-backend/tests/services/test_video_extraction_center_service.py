from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.links import UserSubscription
from models.subscription import Subscription
from models.video_extraction_projection import VideoExtractionProjection
from services import video_extraction_center_service
from services import video_extraction_projection_service


def _reset_extraction_site_catalog_cache(monkeypatch):
    monkeypatch.setattr(video_extraction_center_service, '_site_catalog_cache', None)
    monkeypatch.setattr(video_extraction_center_service, '_site_catalog_cache_expires_at_monotonic', None)
    monkeypatch.setattr(video_extraction_center_service, '_site_icon_url_cache', {})


@contextmanager
def _managed_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _setup_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            Subscription.__table__,
            UserSubscription.__table__,
            CrawlJob.__table__,
            CrawlTask.__table__,
            VideoExtractionProjection.__table__,
        ],
    )
    monkeypatch.setattr(video_extraction_center_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(video_extraction_projection_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(video_extraction_projection_service, '_last_reconcile_monotonic', None, raising=False)
    monkeypatch.setattr(video_extraction_projection_service, '_group_key_layout_checked', False, raising=False)
    return engine


def _seed_tasks(engine):
    now = datetime(2026, 4, 2, 16, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=1,
                type='CHANNEL',
                name='Extract Running',
                url='https://www.youtube.com/channel/extract-running',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=2,
                type='CHANNEL',
                name='Extract Queued',
                url='https://space.bilibili.com/extract-queued',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=3,
                type='CHANNEL',
                name='Extract Success',
                url='https://www.youtube.com/channel/extract-success',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=4,
                type='CHANNEL',
                name='Extract Failed',
                url='https://www.youtube.com/channel/extract-failed',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
        ])
        session.add_all([
            UserSubscription(id=1, user_id=1, subscription_id=1, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=2, user_id=1, subscription_id=2, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=3, user_id=1, subscription_id=3, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=4, user_id=1, subscription_id=4, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
        ])
        session.add_all([
            CrawlJob(id=101, job_type='video_extract', source_type='subscription_sync', site='youtube.com', subscription_id=1, status='running', created_at=now - timedelta(minutes=5), updated_at=now - timedelta(minutes=1)),
            CrawlJob(id=102, job_type='video_extract', source_type='subscription_sync', site='bilibili.com', subscription_id=2, status='pending', created_at=now - timedelta(minutes=4), updated_at=now - timedelta(minutes=2)),
            CrawlJob(id=103, job_type='video_extract', source_type='subscription_sync', site='youtube.com', subscription_id=3, status='succeeded', created_at=now - timedelta(minutes=8), updated_at=now - timedelta(minutes=3), finished_at=now - timedelta(minutes=3)),
            CrawlJob(id=104, job_type='video_extract', source_type='subscription_sync', site='youtube.com', subscription_id=4, status='partial_failed', created_at=now - timedelta(minutes=7), updated_at=now - timedelta(minutes=1), finished_at=now - timedelta(minutes=1)),
        ])
        session.add_all([
            CrawlTask(
                id=1001,
                job_id=101,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='succeeded',
                payload={'sync_state_id': 501},
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=3),
                started_at=now - timedelta(minutes=5),
                finished_at=now - timedelta(minutes=3),
            ),
            CrawlTask(
                id=1002,
                job_id=101,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='running',
                worker_id='worker-a',
                payload={'sync_state_id': 501},
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=1003,
                job_id=101,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='pending',
                payload={'sync_state_id': 501},
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=1),
            ),
            CrawlTask(
                id=2001,
                job_id=102,
                task_type='video_extract',
                site='bilibili.com',
                subscription_id=2,
                status='pending',
                payload={'sync_state_id': 502, 'is_extract_all': True},
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=4),
            ),
            CrawlTask(
                id=2002,
                job_id=102,
                task_type='video_extract',
                site='bilibili.com',
                subscription_id=2,
                status='retry_wait',
                payload={'sync_state_id': 502, 'is_extract_all': True},
                created_at=now - timedelta(minutes=3),
                updated_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=3001,
                job_id=103,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=3,
                status='succeeded',
                payload={'sync_state_id': 503},
                created_at=now - timedelta(minutes=8),
                updated_at=now - timedelta(minutes=4),
                started_at=now - timedelta(minutes=8),
                finished_at=now - timedelta(minutes=4),
            ),
            CrawlTask(
                id=3002,
                job_id=103,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=3,
                status='succeeded',
                payload={'sync_state_id': 503},
                created_at=now - timedelta(minutes=7),
                updated_at=now - timedelta(minutes=3),
                started_at=now - timedelta(minutes=7),
                finished_at=now - timedelta(minutes=3),
            ),
            CrawlTask(
                id=4001,
                job_id=104,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=4,
                status='succeeded',
                payload={'sync_state_id': 504},
                created_at=now - timedelta(minutes=7),
                updated_at=now - timedelta(minutes=2),
                started_at=now - timedelta(minutes=7),
                finished_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=4002,
                job_id=104,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=4,
                status='dead',
                last_error='extract_failed',
                payload={'sync_state_id': 504},
                created_at=now - timedelta(minutes=6),
                updated_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=6),
                finished_at=now - timedelta(minutes=1),
            ),
        ])
        session.commit()


def test_extraction_center_lists_running_queued_and_recent_batches(monkeypatch):
    engine = _setup_env(monkeypatch)
    _seed_tasks(engine)

    overview = video_extraction_center_service.get_extraction_center_overview(user_id=1)
    running_result = video_extraction_center_service.list_extraction_center_items(
        user_id=1,
        status='running',
        site=None,
        query=None,
        page=1,
        page_size=20,
    )
    queued_result = video_extraction_center_service.list_extraction_center_items(
        user_id=1,
        status='queued',
        site=None,
        query=None,
        page=1,
        page_size=20,
    )
    recent_result = video_extraction_center_service.list_extraction_center_items(
        user_id=1,
        status='recent',
        site=None,
        query=None,
        page=1,
        page_size=20,
    )

    assert overview.running_count == 1
    assert overview.queued_count == 1
    assert overview.failed_count == 1
    assert overview.pending_videos == 4

    assert [item.subscription_name for item in running_result.data] == ['Extract Running']
    running_item = running_result.data[0]
    assert running_item.current_phase == 'extracting'
    assert running_item.batch_task_count == 3
    assert running_item.queued_task_count == 1
    assert running_item.running_task_count == 1
    assert running_item.completed_task_count == 1
    assert running_item.failed_task_count == 0
    assert running_item.sync_mode == 'incremental'
    assert running_item.progress_percent == 33
    assert running_item.progress_label == '1 / 3'

    assert [item.subscription_name for item in queued_result.data] == ['Extract Queued']
    assert [item.queue_position for item in queued_result.data] == [1]
    queued_item = queued_result.data[0]
    assert queued_item.current_phase == 'queued'
    assert queued_item.batch_task_count == 2
    assert queued_item.queued_task_count == 2
    assert queued_item.running_task_count == 0
    assert queued_item.completed_task_count == 0
    assert queued_item.sync_mode == 'full'

    assert [item.subscription_name for item in recent_result.data] == ['Extract Failed', 'Extract Success']
    assert recent_result.data[0].sync_status == 'failed'
    assert recent_result.data[0].failed_task_count == 1
    assert recent_result.data[0].sync_mode == 'incremental'
    assert recent_result.data[1].sync_status == 'success'
    assert recent_result.data[1].completed_task_count == 2
    assert recent_result.data[1].sync_mode == 'incremental'


def test_extraction_dashboard_snapshot_does_not_trim_running_or_queued_items(monkeypatch):
    engine = _setup_env(monkeypatch)
    _seed_tasks(engine)
    now = datetime(2026, 4, 2, 16, 10, 0)

    with Session(engine, expire_on_commit=False) as session:
        session.add_all([
            Subscription(
                id=5,
                type='CHANNEL',
                name='Extract Running 2',
                url='https://www.youtube.com/channel/extract-running-2',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            Subscription(
                id=6,
                type='CHANNEL',
                name='Extract Queued 2',
                url='https://space.bilibili.com/extract-queued-2',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            ),
            UserSubscription(id=5, user_id=1, subscription_id=5, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            UserSubscription(id=6, user_id=1, subscription_id=6, is_deleted=False, is_nsfw=False, created_at=now, updated_at=now),
            CrawlJob(
                id=105,
                job_type='video_extract',
                source_type='subscription_sync',
                site='youtube.com',
                subscription_id=5,
                status='running',
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=1),
            ),
            CrawlJob(
                id=106,
                job_type='video_extract',
                source_type='subscription_sync',
                site='bilibili.com',
                subscription_id=6,
                status='pending',
                created_at=now - timedelta(minutes=3),
                updated_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=5001,
                job_id=105,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=5,
                status='running',
                worker_id='worker-b',
                payload={'sync_state_id': 505},
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=5002,
                job_id=105,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=5,
                status='pending',
                payload={'sync_state_id': 505},
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=1),
            ),
            CrawlTask(
                id=6001,
                job_id=106,
                task_type='video_extract',
                site='bilibili.com',
                subscription_id=6,
                status='pending',
                payload={'sync_state_id': 506},
                created_at=now - timedelta(minutes=3),
                updated_at=now - timedelta(minutes=3),
            ),
            CrawlTask(
                id=6002,
                job_id=106,
                task_type='video_extract',
                site='bilibili.com',
                subscription_id=6,
                status='retry_wait',
                payload={'sync_state_id': 506},
                created_at=now - timedelta(minutes=2),
                updated_at=now - timedelta(minutes=2),
            ),
        ])
        session.commit()

    snapshot = video_extraction_center_service.get_extraction_dashboard_snapshot(user_id=1, preview_limit=1)

    assert sorted(item.subscription_name for item in snapshot['runningPreview']) == ['Extract Running', 'Extract Running 2']
    assert sorted(item.subscription_name for item in snapshot['queuedPreview']) == ['Extract Queued', 'Extract Queued 2']


def test_extraction_dashboard_snapshot_reuses_site_catalog_for_icon_resolution(monkeypatch):
    engine = _setup_env(monkeypatch)
    _seed_tasks(engine)
    _reset_extraction_site_catalog_cache(monkeypatch)

    calls = []

    def _fake_get_effective_site_catalog():
        calls.append(1)
        return {
            'youtube': {
                'domains': ['youtube.com', 'youtu.be'],
                'icon_url': '/api/sites/youtube/icon',
            },
            'bilibili': {
                'domains': ['bilibili.com', 'b23.tv'],
                'icon_url': '/api/sites/bilibili/icon',
            },
        }

    monkeypatch.setattr(video_extraction_center_service, 'get_effective_site_catalog', _fake_get_effective_site_catalog)

    snapshot = video_extraction_center_service.get_extraction_dashboard_snapshot(user_id=1)

    assert snapshot['runningPreview'][0].site_icon_url == '/api/sites/youtube/icon'
    assert snapshot['queuedPreview'][0].site_icon_url == '/api/sites/bilibili/icon'
    assert snapshot['recentPreview'][0].site_icon_url == '/api/sites/youtube/icon'
    assert len(calls) == 1


def test_extraction_site_icon_resolution_degrades_when_site_catalog_load_fails(monkeypatch):
    _reset_extraction_site_catalog_cache(monkeypatch)
    monkeypatch.setattr(
        video_extraction_center_service,
        'get_effective_site_catalog',
        lambda: (_ for _ in ()).throw(PermissionError('installations.json is locked')),
    )

    icon_url = video_extraction_center_service._resolve_site_icon_url('youtube.com')

    assert icon_url is None


def test_extraction_center_groups_tasks_by_job_when_sync_state_id_missing(monkeypatch):
    engine = _setup_env(monkeypatch)
    now = datetime(2026, 4, 2, 18, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=10,
                type='CHANNEL',
                name='Fallback Group',
                url='https://www.youtube.com/channel/fallback-group',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserSubscription(
                id=10,
                user_id=1,
                subscription_id=10,
                is_deleted=False,
                is_nsfw=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            CrawlJob(
                id=110,
                job_type='video_extract',
                source_type='subscription_sync',
                site='youtube.com',
                subscription_id=10,
                status='running',
                created_at=now - timedelta(minutes=3),
                updated_at=now - timedelta(minutes=1),
            )
        )
        session.add_all([
            CrawlTask(
                id=11001,
                job_id=110,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=10,
                status='running',
                payload={},
                created_at=now - timedelta(minutes=3),
                updated_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=11002,
                job_id=110,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=10,
                status='pending',
                payload={'sync_state_id': ''},
                created_at=now - timedelta(minutes=2),
                updated_at=now - timedelta(minutes=1),
            ),
        ])
        session.commit()

    running_result = video_extraction_center_service.list_extraction_center_items(
        user_id=1,
        status='running',
        site=None,
        query='Fallback',
        page=1,
        page_size=20,
    )

    assert running_result.total == 1
    assert len(running_result.data) == 1
    assert running_result.data[0].run_id == 'extract:job:110'
    assert running_result.data[0].batch_task_count == 2
    assert running_result.data[0].queued_task_count == 1
    assert running_result.data[0].running_task_count == 1


def test_extraction_center_separates_reused_sync_state_by_run_id(monkeypatch):
    engine = _setup_env(monkeypatch)
    now = datetime(2026, 4, 2, 19, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=15,
                type='CHANNEL',
                name='YouTube Reused State',
                url='https://www.youtube.com/channel/reused-state',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserSubscription(
                id=15,
                user_id=1,
                subscription_id=15,
                is_deleted=False,
                is_nsfw=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add_all([
            CrawlJob(
                id=115,
                job_type='video_extract',
                source_type='subscription_sync',
                site='youtube.com',
                subscription_id=15,
                status='partial_failed',
                created_at=now - timedelta(minutes=12),
                updated_at=now - timedelta(minutes=10),
                finished_at=now - timedelta(minutes=10),
            ),
            CrawlJob(
                id=116,
                job_type='video_extract',
                source_type='subscription_sync',
                site='youtube.com',
                subscription_id=15,
                status='succeeded',
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=1),
                finished_at=now - timedelta(minutes=1),
            ),
        ])
        session.add_all([
            CrawlTask(
                id=11501,
                job_id=115,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=15,
                status='dead',
                last_error='extract_failed',
                payload={'sync_state_id': 880, 'run_id': 'run-old'},
                created_at=now - timedelta(minutes=12),
                updated_at=now - timedelta(minutes=10),
                started_at=now - timedelta(minutes=12),
                finished_at=now - timedelta(minutes=10),
            ),
            CrawlTask(
                id=11502,
                job_id=115,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=15,
                status='dead',
                last_error='extract_failed',
                payload={'sync_state_id': 880, 'run_id': 'run-old'},
                created_at=now - timedelta(minutes=11),
                updated_at=now - timedelta(minutes=10),
                started_at=now - timedelta(minutes=11),
                finished_at=now - timedelta(minutes=10),
            ),
            CrawlTask(
                id=11601,
                job_id=116,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=15,
                status='succeeded',
                payload={'sync_state_id': 880, 'run_id': 'run-new'},
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=2),
                started_at=now - timedelta(minutes=4),
                finished_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=11602,
                job_id=116,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=15,
                status='succeeded',
                payload={'sync_state_id': 880, 'run_id': 'run-new'},
                created_at=now - timedelta(minutes=3),
                updated_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=3),
                finished_at=now - timedelta(minutes=1),
            ),
        ])
        session.commit()

    recent_result = video_extraction_center_service.list_extraction_center_items(
        user_id=1,
        status='recent',
        site=None,
        query='Reused State',
        page=1,
        page_size=20,
    )

    assert recent_result.total == 2
    assert [item.run_id for item in recent_result.data] == ['extract:run:run-new', 'extract:run:run-old']
    assert [item.sync_status for item in recent_result.data] == ['success', 'failed']
    assert [item.batch_task_count for item in recent_result.data] == [2, 2]
    assert [item.completed_task_count for item in recent_result.data] == [2, 0]
    assert [item.failed_task_count for item in recent_result.data] == [0, 2]


def test_extraction_center_reconciles_stale_active_projection(monkeypatch):
    engine = _setup_env(monkeypatch)
    now = datetime(2026, 4, 2, 20, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            Subscription(
                id=20,
                type='CHANNEL',
                name='Projection Drift',
                url='https://www.youtube.com/channel/projection-drift',
                avatar=None,
                description=None,
                total_videos=0,
                is_deleted=False,
                extra_data={},
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            UserSubscription(
                id=20,
                user_id=1,
                subscription_id=20,
                is_deleted=False,
                is_nsfw=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            CrawlJob(
                id=120,
                job_type='video_extract',
                source_type='subscription_sync',
                site='youtube.com',
                subscription_id=20,
                status='succeeded',
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=1),
                finished_at=now - timedelta(minutes=1),
            )
        )
        session.add_all([
            CrawlTask(
                id=12001,
                job_id=120,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=20,
                status='succeeded',
                payload={'sync_state_id': 900},
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=2),
                started_at=now - timedelta(minutes=5),
                finished_at=now - timedelta(minutes=2),
            ),
            CrawlTask(
                id=12002,
                job_id=120,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=20,
                status='succeeded',
                payload={'sync_state_id': 900},
                created_at=now - timedelta(minutes=4),
                updated_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=4),
                finished_at=now - timedelta(minutes=1),
            ),
        ])
        session.add(
            VideoExtractionProjection(
                subscription_id=20,
                group_kind='state',
                group_value='900',
                site='youtube.com',
                sync_status='running',
                display_status='running',
                current_phase='extracting',
                queued_at=now - timedelta(minutes=5),
                locked_at=now - timedelta(minutes=5),
                pending_video_count=24,
                batch_task_count=26,
                queued_task_count=23,
                running_task_count=1,
                completed_task_count=2,
                failed_task_count=0,
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=5),
            )
        )
        session.commit()

    overview = video_extraction_center_service.get_extraction_center_overview(user_id=1)
    running_result = video_extraction_center_service.list_extraction_center_items(
        user_id=1,
        status='running',
        site=None,
        query='Projection Drift',
        page=1,
        page_size=20,
    )
    recent_result = video_extraction_center_service.list_extraction_center_items(
        user_id=1,
        status='recent',
        site=None,
        query='Projection Drift',
        page=1,
        page_size=20,
    )

    assert overview.running_count == 0
    assert overview.pending_videos == 0
    assert running_result.total == 0
    assert recent_result.total == 1
    assert recent_result.data[0].sync_status == 'success'
    assert recent_result.data[0].completed_task_count == 2

