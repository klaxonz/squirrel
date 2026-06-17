from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.subscription.domain.models.crawl_dispatch_scope import CrawlDispatchScope
from domains.subscription.domain.models.crawl_job import CrawlJob
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.video.application.services.extraction.task_service import VideoExtractionTaskService
from domains.video.interfaces.dto.dto.video_dto import VideoExtractDto
from infrastructure.database.base import Base


@pytest.fixture
def engine():
    _engine = create_engine("sqlite:///:memory:")
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
    )


def test_enqueue_writes_crawl_task_when_site_enabled(engine, svc):
    params = VideoExtractDto(
        url="https://www.youtube.com/watch?v=demo",
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id="run-1",
        trigger="manual",
        is_manual=True,
        is_extract_all=False,
    )

    queued = svc.enqueue(params)

    assert queued is True

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()

    assert len(jobs) == 1
    assert jobs[0].job_type == "video_extract"
    assert jobs[0].site == "youtube.com"
    assert len(tasks) == 1
    assert tasks[0].task_type == "video_extract"
    assert tasks[0].video_url == "https://www.youtube.com/watch?v=demo"
    assert tasks[0].payload["run_id"] == "run-1"


def test_enqueue_uses_task_dedupe_for_scheduled_extraction(engine, svc):
    params = VideoExtractDto(
        url="https://www.youtube.com/watch?v=demo",
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id="run-1",
        trigger="scheduled",
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
    assert tasks[0].dedupe_key == "dedupe:video_extract:https://www.youtube.com/watch?v=demo"


def test_enqueue_deduplicates_same_url_across_full_and_incremental(engine, svc):
    full_params = VideoExtractDto(
        url="https://www.youtube.com/watch?v=demo",
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=2,
        run_id="run-full",
        trigger="scheduled",
        is_manual=False,
        is_extract_all=True,
    )
    incr_params = VideoExtractDto(
        url="https://www.youtube.com/watch?v=demo",
        subscribed=True,
        only_extract=True,
        subscription_id=1,
        sync_state_id=3,
        run_id="run-incr",
        trigger="scheduled",
        is_manual=False,
        is_extract_all=False,
    )

    first = svc.enqueue(full_params)
    second = svc.enqueue(incr_params)

    assert first is True
    assert second is False

    with Session(engine, expire_on_commit=False) as session:
        tasks = session.query(CrawlTask).all()

    assert len(tasks) == 1
    assert tasks[0].priority == "full"
    assert tasks[0].dedupe_key == "dedupe:video_extract:https://www.youtube.com/watch?v=demo"
