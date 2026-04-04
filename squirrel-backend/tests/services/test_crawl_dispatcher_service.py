from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from services.crawl_dispatcher.policy import CrawlDispatcherPolicy
from services.crawl_dispatcher.service import CrawlDispatcherService
from services.crawl_tasks import service as crawl_task_service


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


def _setup_test_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[CrawlJob.__table__, CrawlTask.__table__, CrawlDispatchScope.__table__],
    )
    monkeypatch.setattr(crawl_task_service, 'get_session', lambda: _managed_session(engine))
    return engine


def _create_job(session, *, site: str = 'youtube') -> int:
    job = CrawlJob(
        job_type='subscription_sync',
        source_type='manual',
        site=site,
        subscription_id=1,
        payload={},
    )
    session.add(job)
    session.flush()
    return job.id


def test_dispatcher_skips_site_when_site_quota_is_full(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        youtube_job_id = _create_job(session, site='youtube')
        bilibili_job_id = _create_job(session, site='bilibili')
        session.add(
            CrawlTask(
                job_id=youtube_job_id,
                task_type='video_extract',
                site='youtube',
                priority='normal',
                payload={},
                status='running',
                worker_id='worker-hot',
                lease_until=now + timedelta(minutes=5),
            )
        )
        session.add(
            CrawlTask(
                job_id=youtube_job_id,
                task_type='video_extract',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            )
        )
        session.add(
            CrawlTask(
                job_id=bilibili_job_id,
                task_type='video_extract',
                site='bilibili',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            )
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=1),
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.site == 'bilibili'


def test_dispatcher_skips_task_type_when_quota_is_full(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        youtube_job_id = _create_job(session, site='youtube')
        bilibili_job_id = _create_job(session, site='bilibili')
        session.add(
            CrawlTask(
                job_id=youtube_job_id,
                task_type='subscription_sync',
                site='youtube',
                priority='normal',
                payload={},
                status='running',
                worker_id='worker-sync',
                lease_until=now + timedelta(minutes=5),
            )
        )
        session.add(
            CrawlTask(
                job_id=youtube_job_id,
                task_type='subscription_sync',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            )
        )
        session.add(
            CrawlTask(
                job_id=bilibili_job_id,
                task_type='video_extract',
                site='bilibili',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            )
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={'subscription_sync': 1, 'video_extract': 4},
        ),
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.task_type == 'video_extract'


def test_dispatcher_respects_priority_within_available_capacity(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        job_id = _create_job(session, site='youtube')
        session.add(
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube',
                priority='low',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            )
        )
        session.add(
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube',
                priority='manual',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            )
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=2),
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.priority == 'manual'


def test_dispatcher_claim_next_creates_missing_dispatch_scopes_for_legacy_tasks(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        job_id = _create_job(session, site='youtube')
        session.add(
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            )
        )
        session.commit()
        session.query(CrawlDispatchScope).delete()
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=2),
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    with Session(engine, expire_on_commit=False) as session:
        scopes = session.query(CrawlDispatchScope).order_by(CrawlDispatchScope.scope_type, CrawlDispatchScope.scope_key).all()

    assert [(scope.scope_type, scope.scope_key) for scope in scopes] == [
        ('site', 'youtube'),
        ('task_type', 'video_extract'),
    ]


def test_dispatcher_considers_other_sites_when_one_site_fills_candidate_window(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        youtube_job_id = _create_job(session, site='youtube')
        bilibili_job_id = _create_job(session, site='bilibili')
        for index in range(101):
            session.add(
                CrawlTask(
                    job_id=youtube_job_id,
                    task_type='video_extract',
                    site='youtube',
                    priority='normal',
                    payload={},
                    next_run_at=now - timedelta(seconds=200 + index),
                    created_at=now - timedelta(seconds=200 + index),
                )
            )
        session.add(
            CrawlTask(
                job_id=bilibili_job_id,
                task_type='video_extract',
                site='bilibili',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
                created_at=now - timedelta(seconds=1),
            )
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=1),
    )

    first = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)
    second = dispatcher.claim_next(worker_id='worker-2', now=now, lease_seconds=60)

    assert first is not None
    assert second is not None
    assert {first.site, second.site} == {'youtube', 'bilibili'}


def test_dispatcher_considers_other_task_types_when_one_type_fills_candidate_window(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        for index in range(101):
            job_id = _create_job(session, site=f'video-site-{index}')
            session.add(
                CrawlTask(
                    job_id=job_id,
                    task_type='video_extract',
                    site=f'video-site-{index}',
                    priority='normal',
                    payload={},
                    next_run_at=now - timedelta(seconds=200 + index),
                    created_at=now - timedelta(seconds=200 + index),
                )
            )

        sync_job_id = _create_job(session, site='sync-site')
        session.add(
            CrawlTask(
                job_id=sync_job_id,
                task_type='subscription_sync',
                site='sync-site',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
                created_at=now - timedelta(seconds=1),
            )
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=1,
            task_type_limits={'video_extract': 1, 'subscription_sync': 1},
        ),
    )

    first = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)
    second = dispatcher.claim_next(worker_id='worker-2', now=now, lease_seconds=60)

    assert first is not None
    assert first.task_type == 'video_extract'
    assert second is not None
    assert second.task_type == 'subscription_sync'


def test_dispatcher_rotates_sites_before_filling_second_slot_for_one_hot_site(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        hot_job_id = _create_job(session, site='youtube')
        cold_job_id = _create_job(session, site='bilibili')
        session.add(
            CrawlTask(
                job_id=hot_job_id,
                task_type='video_extract',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=200),
                created_at=now - timedelta(seconds=200),
            )
        )
        session.add(
            CrawlTask(
                job_id=hot_job_id,
                task_type='video_extract',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=100),
                created_at=now - timedelta(seconds=100),
            )
        )
        session.add(
            CrawlTask(
                job_id=cold_job_id,
                task_type='video_extract',
                site='bilibili',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
                created_at=now - timedelta(seconds=1),
            )
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=2),
    )

    first = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)
    second = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert first is not None
    assert second is not None
    assert first.site == 'youtube'
    assert second.site == 'bilibili'


def test_dispatcher_gives_subscription_sync_a_slot_when_video_extract_backlog_is_older(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        sync_job_id = _create_job(session, site='youtube')
        session.add(
            CrawlTask(
                job_id=sync_job_id,
                task_type='subscription_sync',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
                created_at=now - timedelta(seconds=1),
            )
        )
        for index in range(20):
            job_id = _create_job(session, site=f'video-site-{index}')
            session.add(
                CrawlTask(
                    job_id=job_id,
                    task_type='video_extract',
                    site=f'video-site-{index}',
                    priority='normal',
                    payload={},
                    next_run_at=now - timedelta(seconds=200 + index),
                    created_at=now - timedelta(seconds=200 + index),
                )
            )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={'subscription_sync': 2, 'video_extract': 8},
        ),
    )

    claimed = [
        dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)
        for _ in range(8)
    ]

    assert any(task is not None and task.task_type == 'subscription_sync' for task in claimed)


def test_dispatcher_considers_next_task_type_for_same_site_when_site_head_type_is_full(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        youtube_job_id = _create_job(session, site='youtube')
        bilibili_job_id = _create_job(session, site='bilibili')

        session.add_all(
            [
                CrawlTask(
                    job_id=youtube_job_id,
                    task_type='video_extract',
                    site='youtube',
                    priority='normal',
                    payload={},
                    status='running',
                    worker_id='worker-youtube-1',
                    lease_until=now + timedelta(minutes=5),
                ),
                CrawlTask(
                    job_id=youtube_job_id,
                    task_type='video_extract',
                    site='youtube',
                    priority='normal',
                    payload={},
                    status='running',
                    worker_id='worker-youtube-2',
                    lease_until=now + timedelta(minutes=5),
                ),
                CrawlTask(
                    job_id=youtube_job_id,
                    task_type='video_extract',
                    site='youtube',
                    priority='normal',
                    payload={},
                    next_run_at=now - timedelta(seconds=300),
                    created_at=now - timedelta(seconds=300),
                ),
                CrawlTask(
                    job_id=bilibili_job_id,
                    task_type='subscription_sync',
                    site='bilibili',
                    priority='normal',
                    payload={},
                    status='running',
                    worker_id='worker-sync',
                    lease_until=now + timedelta(minutes=5),
                ),
                CrawlTask(
                    job_id=bilibili_job_id,
                    task_type='subscription_sync',
                    site='bilibili',
                    priority='normal',
                    payload={},
                    next_run_at=now - timedelta(seconds=200),
                    created_at=now - timedelta(seconds=200),
                ),
                CrawlTask(
                    job_id=bilibili_job_id,
                    task_type='video_extract',
                    site='bilibili',
                    priority='normal',
                    payload={},
                    next_run_at=now - timedelta(seconds=100),
                    created_at=now - timedelta(seconds=100),
                ),
            ]
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={'subscription_sync': 1, 'video_extract': 8},
        ),
    )

    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.site == 'bilibili'
    assert claimed.task_type == 'video_extract'


def test_dispatcher_treats_full_and_incremental_sync_as_separate_task_types(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        job_id = _create_job(session, site='youtube')
        session.add_all(
            [
                CrawlTask(
                    job_id=job_id,
                    task_type='subscription_sync_full',
                    site='youtube',
                    priority='normal',
                    payload={'mode': 'full'},
                    status='running',
                    worker_id='worker-full',
                    lease_until=now + timedelta(minutes=5),
                ),
                CrawlTask(
                    job_id=job_id,
                    task_type='subscription_sync_full',
                    site='youtube',
                    priority='normal',
                    payload={'mode': 'full'},
                    next_run_at=now - timedelta(seconds=2),
                ),
                CrawlTask(
                    job_id=job_id,
                    task_type='subscription_sync_incremental',
                    site='youtube',
                    priority='normal',
                    payload={'mode': 'incremental'},
                    next_run_at=now - timedelta(seconds=1),
                ),
            ]
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=3,
            task_type_limits={'subscription_sync_full': 1, 'subscription_sync_incremental': 2},
        ),
    )

    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.task_type == 'subscription_sync_incremental'
