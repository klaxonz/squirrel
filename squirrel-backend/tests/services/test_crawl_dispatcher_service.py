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
    Base.metadata.create_all(engine, tables=[CrawlJob.__table__, CrawlTask.__table__])
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
