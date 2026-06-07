from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from services.crawl_dispatcher.policy import CrawlDispatcherPolicy
from services.crawl_dispatcher.service import CrawlDispatcherService
from services.crawl_tasks.service import CrawlTaskService


@pytest.fixture
def svc(session_factory):
    return CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={},
        ),
        session_factory=session_factory,
    )


def _create_tables(engine):
    Base.metadata.create_all(
        engine,
        tables=[CrawlJob.__table__, CrawlTask.__table__, CrawlDispatchScope.__table__],
    )


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


def test_dispatcher_skips_site_when_site_quota_is_full(engine, svc):
    _create_tables(engine)
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
            ),
        )
        session.add(
            CrawlTask(
                job_id=youtube_job_id,
                task_type='video_extract',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            ),
        )
        session.add(
            CrawlTask(
                job_id=bilibili_job_id,
                task_type='video_extract',
                site='bilibili',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            ),
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=1),
        session_factory=svc.session_factory,
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.site == 'bilibili'


def test_dispatcher_skips_task_type_when_quota_is_full(engine, svc):
    _create_tables(engine)
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
            ),
        )
        session.add(
            CrawlTask(
                job_id=youtube_job_id,
                task_type='subscription_sync',
                site='youtube',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            ),
        )
        session.add(
            CrawlTask(
                job_id=bilibili_job_id,
                task_type='video_extract',
                site='bilibili',
                priority='normal',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            ),
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={'subscription_sync': 1, 'video_extract': 4},
        ),
        session_factory=svc.session_factory,
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.task_type == 'video_extract'


def test_dispatcher_respects_priority_within_available_capacity(engine, svc):
    _create_tables(engine)
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
            ),
        )
        session.add(
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube',
                priority='manual',
                payload={},
                next_run_at=now - timedelta(seconds=1),
            ),
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=2),
        session_factory=svc.session_factory,
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.priority == 'manual'


def test_dispatcher_claim_next_creates_missing_dispatch_scopes_for_legacy_tasks(engine, svc):
    _create_tables(engine)
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
            ),
        )
        session.commit()
        session.query(CrawlDispatchScope).delete()
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=2),
        session_factory=svc.session_factory,
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    with Session(engine, expire_on_commit=False) as session:
        scopes = (
            session.query(CrawlDispatchScope)
            .order_by(CrawlDispatchScope.scope_type, CrawlDispatchScope.scope_key)
            .all()
        )

    assert [(scope.scope_type, scope.scope_key) for scope in scopes] == [
        ('site', 'youtube'),
        ('task_type', 'video_extract'),
    ]


def test_dispatcher_considers_other_sites_when_one_site_fills_candidate_window(engine, svc):
    _create_tables(engine)
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
                ),
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
            ),
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=1),
        session_factory=svc.session_factory,
    )

    first = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)
    second = dispatcher.claim_next(worker_id='worker-2', now=now, lease_seconds=60)

    assert first is not None
    assert second is not None
    assert {first.site, second.site} == {'youtube', 'bilibili'}


def test_dispatcher_considers_other_task_types_when_one_type_fills_candidate_window(engine, svc):
    _create_tables(engine)
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
                ),
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
            ),
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=1,
            task_type_limits={'video_extract': 1, 'subscription_sync': 1},
        ),
        session_factory=svc.session_factory,
    )

    first = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)
    second = dispatcher.claim_next(worker_id='worker-2', now=now, lease_seconds=60)

    assert first is not None
    assert first.task_type == 'video_extract'
    assert second is not None
    assert second.task_type == 'subscription_sync'


def test_dispatcher_rotates_sites_before_filling_second_slot_for_one_hot_site(engine, svc):
    _create_tables(engine)
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
            ),
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
            ),
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
            ),
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(default_site_concurrency=2),
        session_factory=svc.session_factory,
    )

    first = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)
    second = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert first is not None
    assert second is not None
    assert first.site == 'youtube'
    assert second.site == 'bilibili'


def test_dispatcher_gives_subscription_sync_a_slot_when_video_extract_backlog_is_older(engine, svc):
    _create_tables(engine)
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
            ),
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
                ),
            )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={'subscription_sync': 2, 'video_extract': 8},
        ),
        session_factory=svc.session_factory,
    )

    claimed = [dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60) for _ in range(8)]

    assert any(task is not None and task.task_type == 'subscription_sync' for task in claimed)


def test_dispatcher_considers_next_task_type_for_same_site_when_site_head_type_is_full(engine, svc):
    _create_tables(engine)
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
            ],
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={'subscription_sync': 1, 'video_extract': 8},
        ),
        session_factory=svc.session_factory,
    )

    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.site == 'bilibili'
    assert claimed.task_type == 'video_extract'


def test_dispatcher_treats_full_and_incremental_sync_as_separate_task_types(engine, svc):
    _create_tables(engine)
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
            ],
        )
        session.commit()

    dispatcher = CrawlDispatcherService(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=3,
            task_type_limits={'subscription_sync_full': 1, 'subscription_sync_incremental': 2},
        ),
        session_factory=svc.session_factory,
    )

    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.task_type == 'subscription_sync_incremental'


def test_dispatcher_rolls_back_failed_candidate_attempts_before_trying_next_candidate(engine, svc):
    _create_tables(engine)
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
                next_run_at=now - timedelta(seconds=2),
                created_at=now - timedelta(seconds=2),
            ),
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
            ),
        )
        session.commit()

    class FailingFirstClaimDispatcher(CrawlDispatcherService):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._attempt_count = 0
            self._original_try_claim_candidate = CrawlDispatcherService._try_claim_candidate

        def _try_claim_candidate(self, session, *, task_id, worker_id, now, lease_seconds):
            self._attempt_count += 1
            if self._attempt_count == 1:
                CrawlTaskService._ensure_dispatch_scope(
                    session,
                    scope_type='site',
                    scope_key='youtube',
                )
                return None
            return self._original_try_claim_candidate(
                self,
                session,
                task_id=task_id,
                worker_id=worker_id,
                now=now,
                lease_seconds=lease_seconds,
            )

    dispatcher = FailingFirstClaimDispatcher(
        policy=CrawlDispatcherPolicy(default_site_concurrency=2),
        session_factory=svc.session_factory,
    )
    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.site == 'bilibili'

    with Session(engine, expire_on_commit=False) as session:
        scopes = (
            session.query(CrawlDispatchScope)
            .order_by(
                CrawlDispatchScope.scope_type,
                CrawlDispatchScope.scope_key,
            )
            .all()
        )

    assert [(scope.scope_type, scope.scope_key) for scope in scopes] == [
        ('site', 'bilibili'),
        ('task_type', 'video_extract'),
    ]


def test_dispatcher_skips_candidate_when_task_type_scope_is_locked(engine, svc):
    _create_tables(engine)
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
                    next_run_at=now - timedelta(seconds=2),
                    created_at=now - timedelta(seconds=2),
                ),
                CrawlTask(
                    job_id=job_id,
                    task_type='subscription_sync_incremental',
                    site='youtube',
                    priority='normal',
                    payload={'mode': 'incremental'},
                    next_run_at=now - timedelta(seconds=1),
                    created_at=now - timedelta(seconds=1),
                ),
            ],
        )
        session.commit()

    class BusyFullSyncScopeDispatcher(CrawlDispatcherService):
        def _lock_scope(self, session, *, scope_type, scope_key):
            if scope_type == 'task_type' and scope_key == 'subscription_sync_full':
                return None
            return super()._lock_scope(session, scope_type=scope_type, scope_key=scope_key)

    dispatcher = BusyFullSyncScopeDispatcher(
        policy=CrawlDispatcherPolicy(
            default_site_concurrency=2,
            task_type_limits={
                'subscription_sync_full': 1,
                'subscription_sync_incremental': 1,
            },
        ),
        session_factory=svc.session_factory,
    )

    claimed = dispatcher.claim_next(worker_id='worker-1', now=now, lease_seconds=60)

    assert claimed is not None
    assert claimed.task_type == 'subscription_sync_incremental'

    with Session(engine, expire_on_commit=False) as session:
        full_sync_task = session.query(CrawlTask).filter_by(task_type='subscription_sync_full').one()

    assert full_sync_task.status == 'pending'
