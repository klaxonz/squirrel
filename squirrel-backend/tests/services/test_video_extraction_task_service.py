from contextlib import contextmanager
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskStateError
from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.subscription.domain.models.crawl_dispatch_scope import CrawlDispatchScope
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from domains.video.application.services.extraction.task_service import VideoExtractionTaskService
from domains.video.interfaces.dto.video_dto import VideoExtractDto
from infrastructure.database.base import Base


@pytest.fixture
def engine():
    _engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        _engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
        ],
    )
    return _engine


@pytest.fixture
def session_factory(engine):
    @contextmanager
    def _factory():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _factory


@pytest.fixture
def svc(session_factory):
    task_svc = CrawlTaskService(session_factory=session_factory)
    return VideoExtractionTaskService(
        get_video_by_url=lambda url: None,
        crawl_tasks=task_svc,
        reserve_sync_progress=False,
    )


def test_enqueue_writes_crawl_task_when_site_enabled(engine, svc):
    params = VideoExtractDto(
        url='https://www.youtube.com/watch?v=demo',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id='run-1',
        trigger='manual',
        is_manual=True,
        is_extract_all=False,
    )

    queued = svc.enqueue(params)
    duplicate = svc.enqueue(params)

    assert queued is True
    assert duplicate is False

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()

    assert len(jobs) == 1
    assert jobs[0].job_type == 'video_extract'
    assert jobs[0].site == 'youtube.com'
    assert len(tasks) == 1
    assert tasks[0].task_type == 'video_extract'
    assert tasks[0].video_url == 'https://www.youtube.com/watch?v=demo'
    assert tasks[0].sync_state_id == 2
    assert tasks[0].payload['run_id'] == 'run-1'


def test_enqueue_uses_task_dedupe_for_scheduled_extraction(engine, svc):
    params = VideoExtractDto(
        url='https://www.youtube.com/watch?v=demo',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id='run-1',
        trigger='scheduled',
        is_manual=False,
        is_extract_all=False,
    )

    first = svc.enqueue(params)
    second = svc.enqueue(params)

    assert first is True
    assert second is False

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()

    assert len(jobs) == 1
    assert len(tasks) == 1
    assert tasks[0].dedupe_key == svc.build_dedupe_key(params.url, params.subscription_id, params.run_id)


def test_enqueue_keeps_independent_barriers_for_full_and_incremental_runs(engine, svc):
    full_params = VideoExtractDto(
        url='https://www.youtube.com/watch?v=demo',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id='run-full',
        trigger='scheduled',
        is_manual=False,
        is_extract_all=True,
    )
    incr_params = VideoExtractDto(
        url='https://www.youtube.com/watch?v=demo',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=3,
        run_id='run-incr',
        trigger='scheduled',
        is_manual=False,
        is_extract_all=False,
    )

    first = svc.enqueue(full_params)
    second = svc.enqueue(incr_params)

    assert first is True
    assert second is True

    with Session(engine, expire_on_commit=False) as session:
        tasks = session.query(CrawlTask).all()

    assert len(tasks) == 2
    assert tasks[0].priority == 'full'
    assert tasks[1].priority == 'incr'
    assert tasks[0].dedupe_key == svc.build_dedupe_key(
        full_params.url,
        full_params.subscription_id,
        full_params.run_id,
    )
    assert tasks[0].dedupe_key != tasks[1].dedupe_key


def test_enqueue_keeps_same_video_tasks_for_different_subscriptions(engine, svc):
    first = VideoExtractDto(
        url='https://www.youtube.com/watch?v=shared',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        is_manual=False,
    )
    second = first.model_copy(update={'subscription_id': 2})

    assert svc.enqueue(first) is True
    assert svc.enqueue(second) is True

    with Session(engine, expire_on_commit=False) as session:
        tasks = session.query(CrawlTask).order_by(CrawlTask.id).all()
    assert [task.subscription_id for task in tasks] == [1, 2]
    assert tasks[0].dedupe_key != tasks[1].dedupe_key


def test_enqueue_atomically_reserves_current_sync_run(session_factory, engine):
    Base.metadata.create_all(engine, tables=[SubscriptionSyncState.__table__])
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=8,
                subscription_id=1,
                site='youtube',
                sync_mode='incremental',
                sync_status='running',
                next_sync_at=datetime.now(),
                current_run_id='run-8',
                execution_token='direct:run-8',
            ),
        )
        session.commit()

    service = VideoExtractionTaskService(
        get_video_by_url=lambda url: None,
        crawl_tasks=CrawlTaskService(session_factory=session_factory),
    )
    params = VideoExtractDto(
        url='https://www.youtube.com/watch?v=atomic',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=8,
            run_id='run-8',
            parent_execution_token='direct:run-8',
            is_manual=True,
    )

    assert service.enqueue(params) is True
    assert service.enqueue(params) is False
    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 8)
        task = session.query(CrawlTask).filter(CrawlTask.run_id == 'run-8').one()
    assert state.pending_video_count == 1
    assert task.sync_state_id == 8


def test_enqueue_rejects_unfenced_sync_state_task(session_factory):
    service = VideoExtractionTaskService(
        get_video_by_url=lambda url: None,
        crawl_tasks=CrawlTaskService(session_factory=session_factory),
    )
    params = VideoExtractDto(
        url='https://www.youtube.com/watch?v=unfenced',
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=8,
        is_manual=False,
    )

    with pytest.raises(CrawlTaskStateError, match='missing run_id fencing'):
        service.enqueue(params)
