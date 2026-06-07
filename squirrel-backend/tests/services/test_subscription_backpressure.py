from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from models import Base
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.subscription_sync_state import SubscriptionSyncState
from queues.queue_monitor import QueueBackpressureMonitor
from services.crawl_tasks.service import CrawlTaskService


@pytest.fixture
def engine(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            SubscriptionSyncState.__table__,
        ],
    )
    return engine


@pytest.fixture
def svc(session_factory):
    return CrawlTaskService(session_factory=session_factory)


def _seed_job(engine, *, site: str = "youtube.com") -> int:
    with Session(engine, expire_on_commit=False) as session:
        job = CrawlJob(
            job_type="subscription_sync",
            source_type="scheduled",
            site=site,
            subscription_id=1,
            payload={},
        )
        session.add(job)
        session.flush()
        job_id = job.id
        session.commit()
        return job_id


def test_queue_monitor_counts_pending_videos_from_task_store(engine, session_factory, svc):
    with Session(engine, expire_on_commit=False) as session:
        job_id = _seed_job(engine)
        session.add_all([
            CrawlTask(
                job_id=job_id,
                task_type="video_extract",
                site="youtube.com",
                subscription_id=1,
                status="pending",
                payload={"sync_state_id": 10},
            ),
            CrawlTask(
                job_id=job_id,
                task_type="video_extract",
                site="youtube.com",
                subscription_id=1,
                status="running",
                payload={"sync_state_id": 10},
            ),
            CrawlTask(
                job_id=job_id,
                task_type="video_extract",
                site="youtube.com",
                subscription_id=1,
                status="succeeded",
                payload={"sync_state_id": 10},
            ),
        ])
        session.commit()

    count = QueueBackpressureMonitor().count_pending_videos_for_subscription(
        subscription_id=1,
        url="https://www.youtube.com/watch?v=demo",
    )

    assert count == 2


def test_reconcile_pending_video_counts_uses_task_store(engine, session_factory, svc, sss_session):
    from services.subscription_sync_state_service import SyncStateService
    sss_svc = SyncStateService(session_factory=session_factory)

    with Session(engine, expire_on_commit=False) as session:
        job_id = _seed_job(engine)
        session.add(
            SubscriptionSyncState(
                id=10,
                subscription_id=1,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="queued",
                cursor_payload={},
                next_sync_at=datetime(2026, 4, 1, 12, 0, 0),
                pending_video_count=99,
            ),
        )
        session.add_all([
            CrawlTask(
                job_id=job_id,
                task_type="video_extract",
                site="youtube.com",
                subscription_id=1,
                status="pending",
                payload={"sync_state_id": 10},
            ),
            CrawlTask(
                job_id=job_id,
                task_type="video_extract",
                site="youtube.com",
                subscription_id=1,
                status="retry_wait",
                payload={"sync_state_id": 10},
            ),
        ])
        session.commit()

    result = sss_svc.reconcile_pending_video_counts()

    assert result == {"states": 1, "videos": 2}
    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 10)
    assert state.pending_video_count == 2


def test_recover_stale_queued_sync_states_uses_task_store(engine, session_factory, svc, sss_session):
    with Session(engine, expire_on_commit=False) as session:
        job_id = _seed_job(engine)
        session.add(
            SubscriptionSyncState(
                id=10,
                subscription_id=1,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="queued",
                cursor_payload={},
                next_sync_at=datetime(2026, 4, 1, 12, 0, 0),
                queued_at=datetime.now() - timedelta(minutes=10),
            ),
        )
        session.add(
            CrawlTask(
                job_id=job_id,
                task_type="subscription_sync",
                site="youtube.com",
                subscription_id=1,
                status="pending",
                payload={"sync_state_id": 10},
            ),
        )
        session.commit()

    from services.subscription_sync_state_service import SyncStateService
    sss_svc = SyncStateService(session_factory=session_factory)
    result = sss_svc.recover_stale_queued_sync_states()

    assert result["recovered"] == 0
    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 10)
    assert state.sync_status == "queued"


def test_reconcile_terminal_drained_sync_states_auto_completes_running_extract_phase(engine, session_factory, svc, sss_session):
    from services.subscription_sync_state_service import SyncStateService
    sss_svc = SyncStateService(session_factory=session_factory)
    captured_events = []

    import _pytest.monkeypatch as _mp

    from services import subscription_sync_state_service as sss_mod
    mp = _mp.MonkeyPatch()
    try:
        mp.setattr(sss_mod, "append_event", lambda event, session=None: captured_events.append(event))

        with Session(engine, expire_on_commit=False) as session:
            session.add(
                SubscriptionSyncState(
                    id=10,
                    subscription_id=1,
                    site="youtube.com",
                    sync_mode="incremental",
                    sync_status="running",
                    cursor_payload={},
                    last_seen_video_url="https://example.com/video/1",
                    next_sync_at=datetime(2026, 4, 1, 12, 0, 0),
                    last_sync_at=datetime(2026, 4, 1, 11, 50, 0),
                    pending_video_count=3,
                    locked_at=None,
                ),
            )
            session.commit()

        result = sss_svc.reconcile_terminal_drained_sync_states()

        assert result == {"running_states": 1, "completed": 1, "failed": 0}

        with Session(engine, expire_on_commit=False) as session:
            state = session.get(SubscriptionSyncState, 10)

        assert state.sync_status == "success"
        assert state.pending_video_count == 0
        assert state.last_success_at is not None
        assert [event.event_type for event in captured_events] == ["run_created", "completed"]
    finally:
        mp.undo()


def test_reconcile_terminal_drained_sync_states_auto_fails_when_extract_tasks_are_dead(engine, session_factory, svc, sss_session):
    from services.subscription_sync_state_service import SyncStateService
    sss_svc = SyncStateService(session_factory=session_factory)
    captured_events = []

    import _pytest.monkeypatch as _mp

    from services import subscription_sync_state_service as sss_mod
    mp = _mp.MonkeyPatch()
    try:
        mp.setattr(sss_mod, "append_event", lambda event, session=None: captured_events.append(event))

        with Session(engine, expire_on_commit=False) as session:
            job_id = _seed_job(engine)
            session.add(
                SubscriptionSyncState(
                    id=10,
                    subscription_id=1,
                    site="youtube.com",
                    sync_mode="incremental",
                    sync_status="running",
                    cursor_payload={},
                    next_sync_at=datetime(2026, 4, 1, 12, 0, 0),
                    last_sync_at=datetime(2026, 4, 1, 11, 50, 0),
                    pending_video_count=2,
                    locked_at=None,
                ),
            )
            session.add(
                CrawlTask(
                    job_id=job_id,
                    task_type="video_extract",
                    site="youtube.com",
                    subscription_id=1,
                    status="dead",
                    last_error="extract_failed",
                    payload={"sync_state_id": 10},
                ),
            )
            session.commit()

        result = sss_svc.reconcile_terminal_drained_sync_states()

        assert result == {"running_states": 1, "completed": 0, "failed": 1}

        with Session(engine, expire_on_commit=False) as session:
            state = session.get(SubscriptionSyncState, 10)

        assert state.sync_status == "failed"
        assert state.pending_video_count == 0
        assert state.last_error == "extract_failed"
        assert [event.event_type for event in captured_events] == ["run_created", "failed"]
    finally:
        mp.undo()
