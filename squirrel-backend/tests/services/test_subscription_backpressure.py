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
from models.subscription_sync_state import SubscriptionSyncState
from queues.queue_monitor import QueueBackpressureMonitor
from services.crawl_tasks import service as crawl_task_service
from services import subscription_sync_state_service


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
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            SubscriptionSyncState.__table__,
        ],
    )
    monkeypatch.setattr(crawl_task_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(subscription_sync_state_service, 'get_session', lambda: _managed_session(engine))
    return engine


def _seed_job(session, *, site: str = 'youtube.com') -> int:
    job = CrawlJob(
        job_type='subscription_sync',
        source_type='scheduled',
        site=site,
        subscription_id=1,
        payload={},
    )
    session.add(job)
    session.flush()
    return job.id


def test_queue_monitor_counts_pending_videos_from_task_store(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        job_id = _seed_job(session)
        session.add_all([
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='pending',
                payload={'sync_state_id': 10},
            ),
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='running',
                payload={'sync_state_id': 10},
            ),
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='succeeded',
                payload={'sync_state_id': 10},
            ),
        ])
        session.commit()

    count = QueueBackpressureMonitor().count_pending_videos_for_subscription(
        subscription_id=1,
        url='https://www.youtube.com/watch?v=demo',
    )

    assert count == 2


def test_reconcile_pending_video_counts_uses_task_store(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        job_id = _seed_job(session)
        session.add(
            SubscriptionSyncState(
                id=10,
                subscription_id=1,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='queued',
                cursor_payload={},
                next_sync_at=datetime(2026, 4, 1, 12, 0, 0),
                pending_video_count=99,
            )
        )
        session.add_all([
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='pending',
                payload={'sync_state_id': 10},
            ),
            CrawlTask(
                job_id=job_id,
                task_type='video_extract',
                site='youtube.com',
                subscription_id=1,
                status='retry_wait',
                payload={'sync_state_id': 10},
            ),
        ])
        session.commit()

    result = subscription_sync_state_service.reconcile_pending_video_counts()

    assert result == {'states': 1, 'videos': 2}
    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 10)
    assert state.pending_video_count == 2


def test_recover_stale_queued_sync_states_uses_task_store(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    with Session(engine, expire_on_commit=False) as session:
        job_id = _seed_job(session)
        session.add(
            SubscriptionSyncState(
                id=10,
                subscription_id=1,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='queued',
                cursor_payload={},
                next_sync_at=datetime(2026, 4, 1, 12, 0, 0),
                queued_at=datetime.now() - timedelta(minutes=10),
            )
        )
        session.add(
            CrawlTask(
                job_id=job_id,
                task_type='subscription_sync',
                site='youtube.com',
                subscription_id=1,
                status='pending',
                payload={'sync_state_id': 10},
            )
        )
        session.commit()

    result = subscription_sync_state_service.recover_stale_queued_sync_states()

    assert result['recovered'] == 0
    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 10)
    assert state.sync_status == 'queued'
