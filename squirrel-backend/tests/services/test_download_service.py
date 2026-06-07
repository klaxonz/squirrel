import sys
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from schemas.video.dto.video_dto import VideoExtractDto
from services import download_service
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


def _setup_task_store(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
        ],
    )
    monkeypatch.setattr(crawl_task_service, "get_session", lambda: _managed_session(engine))
    return engine


def test_enqueue_video_extraction_writes_crawl_task_when_v2_enabled(monkeypatch):
    engine = _setup_task_store(monkeypatch)

    monkeypatch.setattr(download_service.video_service, "get_video_by_url", lambda url: None)

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

    queued = download_service.enqueue_video_extraction(params)

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


def test_enqueue_video_extraction_uses_task_dedupe_when_v2_enabled(monkeypatch):
    engine = _setup_task_store(monkeypatch)

    monkeypatch.setattr(download_service.video_service, "get_video_by_url", lambda url: None)

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

    first = download_service.enqueue_video_extraction(params)
    second = download_service.enqueue_video_extraction(params)

    assert first is True
    assert second is False

    with Session(engine, expire_on_commit=False) as session:
        jobs = session.query(CrawlJob).all()
        tasks = session.query(CrawlTask).all()

    assert len(jobs) == 1
    assert len(tasks) == 1
    assert tasks[0].dedupe_key == "dedupe:video_extract:https://www.youtube.com/watch?v=demo"


def test_enqueue_video_extraction_deduplicates_same_url_across_full_and_incremental(monkeypatch):
    engine = _setup_task_store(monkeypatch)

    monkeypatch.setattr(download_service.video_service, "get_video_by_url", lambda url: None)

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

    first = download_service.enqueue_video_extraction(full_params)
    second = download_service.enqueue_video_extraction(incr_params)

    assert first is True
    assert second is False

    with Session(engine, expire_on_commit=False) as session:
        tasks = session.query(CrawlTask).all()

    assert len(tasks) == 1
    assert tasks[0].priority == "full"
    assert tasks[0].dedupe_key == "dedupe:video_extract:https://www.youtube.com/watch?v=demo"
