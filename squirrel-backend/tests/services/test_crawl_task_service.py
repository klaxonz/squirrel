import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.crawl_dispatch_scope import CrawlDispatchScope
from models.crawl_job import CrawlJob
from models.crawl_task import CrawlTask
from models.subscription_sync_state import SubscriptionSyncState
from models.video_extraction_projection import VideoExtractionProjection
from services import subscription_sync_state_service, video_extraction_projection_service
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
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            CrawlJob.__table__,
            CrawlTask.__table__,
            CrawlDispatchScope.__table__,
            SubscriptionSyncState.__table__,
            VideoExtractionProjection.__table__,
        ],
    )
    monkeypatch.setattr(crawl_task_service, "get_session", lambda: _managed_session(engine))
    monkeypatch.setattr(subscription_sync_state_service, "get_session", lambda: _managed_session(engine))
    from core import database
    monkeypatch.setattr(database, "get_session", lambda: _managed_session(engine))
    monkeypatch.setattr(video_extraction_projection_service, "get_session", lambda: _managed_session(engine))
    return engine


def _create_job(engine) -> int:
    with Session(engine, expire_on_commit=False) as session:
        job = CrawlJob(
            job_type="subscription_sync",
            source_type="manual",
            site="youtube",
            subscription_id=1,
            payload={},
        )
        session.add(job)
        session.commit()
        return job.id


def test_create_job_and_task_persists_defaults(monkeypatch):
    engine = _setup_test_env(monkeypatch)

    job = crawl_task_service.create_job(
        job_type="subscription_sync",
        source_type="manual",
        site="youtube",
        subscription_id=1,
        payload={"mode": "incremental"},
    )
    task = crawl_task_service.create_task(
        job_id=job.id,
        task_type="video_extract",
        site="youtube",
        payload={"url": "https://example.com/watch?v=1"},
    )

    with Session(engine, expire_on_commit=False) as session:
        stored_job = session.get(CrawlJob, job.id)
        stored_task = session.get(CrawlTask, task.id)
        scopes = session.query(CrawlDispatchScope).order_by(CrawlDispatchScope.scope_type, CrawlDispatchScope.scope_key).all()

    assert stored_job is not None
    assert stored_job.status == "pending"
    assert stored_task is not None
    assert stored_task.status == "pending"
    assert stored_task.attempt == 0
    assert [(scope.scope_type, scope.scope_key) for scope in scopes] == [
        ("site", "youtube"),
        ("task_type", "video_extract"),
    ]


def test_claim_next_task_sets_lease(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            CrawlTask(
                job_id=job_id,
                task_type="video_extract",
                site="youtube",
                priority="normal",
                payload={},
                next_run_at=now - timedelta(minutes=1),
            ),
        )
        session.commit()

    claimed = crawl_task_service.claim_next_task(worker_id="worker-1", now=now, lease_seconds=90)

    assert claimed is not None
    assert claimed.status == "leased"
    assert claimed.worker_id == "worker-1"
    assert claimed.lease_until == now + timedelta(seconds=90)


def test_renew_task_lease_extends_current_lease(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    base_time = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="leased",
            worker_id="worker-1",
            lease_until=base_time + timedelta(seconds=30),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    renewed = crawl_task_service.renew_task_lease(
        task_id=task_id,
        worker_id="worker-1",
        now=base_time,
        lease_seconds=120,
    )

    assert renewed is not None
    assert renewed.lease_until == base_time + timedelta(seconds=120)


def test_recover_expired_tasks_moves_retriable_task_to_retry_wait(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="running",
            worker_id="worker-1",
            attempt=0,
            max_attempts=3,
            lease_until=now - timedelta(seconds=1),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    recovered = crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=45)

    assert recovered == 1

    with Session(engine, expire_on_commit=False) as session:
        stored_task = session.get(CrawlTask, task_id)

    assert stored_task.status == "retry_wait"
    assert stored_task.attempt == 1
    assert stored_task.worker_id is None
    assert stored_task.lease_until is None
    assert stored_task.next_run_at == now + timedelta(seconds=45)


def test_recover_expired_subscription_sync_task_requeues_matching_sync_state(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)
    captured_events = []
    monkeypatch.setattr(subscription_sync_state_service, "append_event", lambda event, session=None: captured_events.append(event))

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=1749,
                subscription_id=1,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="running",
                cursor_payload={},
                queue_token="queue-token-1",
                queued_at=now - timedelta(minutes=2),
                locked_at=now - timedelta(minutes=1),
                next_sync_at=now - timedelta(minutes=5),
            ),
        )
        task = CrawlTask(
            job_id=job_id,
            task_type="subscription_sync_incremental",
            site="youtube.com",
            priority="normal",
            subscription_id=1,
            payload={
                "sync_state_id": 1749,
                "queue_token": "queue-token-1",
                "run_id": "run-requeue-1",
                "request_id": "req-requeue-1",
                "trace_id": "trace-requeue-1",
                "trigger": "scheduled",
            },
            status="running",
            worker_id="worker-1",
            attempt=0,
            max_attempts=3,
            lease_until=now - timedelta(seconds=1),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    recovered = crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=45)

    assert recovered == 1

    with Session(engine, expire_on_commit=False) as session:
        stored_task = session.get(CrawlTask, task_id)
        sync_state = session.get(SubscriptionSyncState, 1749)

    assert stored_task.status == "retry_wait"
    assert sync_state.sync_status == "queued"
    assert sync_state.queue_token == "queue-token-1"
    assert sync_state.locked_at is None
    assert sync_state.queued_at == now
    assert len(captured_events) == 1
    assert captured_events[0].stream_id == "run-requeue-1"
    assert captured_events[0].request_id == "req-requeue-1"
    assert captured_events[0].trace_id == "trace-requeue-1"
    assert captured_events[0].trigger == "scheduled"
    assert captured_events[0].event_type == "queued"
    assert captured_events[0].event_phase == "queued"
    assert captured_events[0].event_status == "queued"
    assert captured_events[0].message == "lease_expired"
    assert captured_events[0].payload["queue_token"] == "queue-token-1"
    assert captured_events[0].payload["pending_video_count"] == 0


def test_recover_expired_tasks_moves_exhausted_task_to_dead(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="running",
            worker_id="worker-1",
            attempt=2,
            max_attempts=3,
            lease_until=now - timedelta(seconds=1),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    recovered = crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=45)

    assert recovered == 1

    with Session(engine, expire_on_commit=False) as session:
        stored_task = session.get(CrawlTask, task_id)

    assert stored_task.status == "dead"
    assert stored_task.attempt == 3
    assert stored_task.finished_at == now


def test_recover_expired_subscription_sync_task_marks_sync_state_failed_when_dead(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)
    captured_events = []
    monkeypatch.setattr(subscription_sync_state_service, "append_event", lambda event, session=None: captured_events.append(event))

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=1750,
                subscription_id=1,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="running",
                cursor_payload={},
                queue_token="queue-token-2",
                queued_at=now - timedelta(minutes=2),
                locked_at=now - timedelta(minutes=1),
                next_sync_at=now - timedelta(minutes=5),
                failure_count=0,
            ),
        )
        task = CrawlTask(
            job_id=job_id,
            task_type="subscription_sync_incremental",
            site="youtube.com",
            priority="normal",
            subscription_id=1,
            payload={
                "sync_state_id": 1750,
                "queue_token": "queue-token-2",
                "run_id": "run-failed-1",
                "request_id": "req-failed-1",
                "trace_id": "trace-failed-1",
                "trigger": "scheduled",
            },
            status="running",
            worker_id="worker-1",
            attempt=2,
            max_attempts=3,
            lease_until=now - timedelta(seconds=1),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    recovered = crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=45)

    assert recovered == 1

    with Session(engine, expire_on_commit=False) as session:
        stored_task = session.get(CrawlTask, task_id)
        sync_state = session.get(SubscriptionSyncState, 1750)

    assert stored_task.status == "dead"
    assert sync_state.sync_status == "failed"
    assert sync_state.queue_token is None
    assert sync_state.locked_at is None
    assert sync_state.failure_count == 1
    assert len(captured_events) == 1
    assert captured_events[0].stream_id == "run-failed-1"
    assert captured_events[0].request_id == "req-failed-1"
    assert captured_events[0].trace_id == "trace-failed-1"
    assert captured_events[0].trigger == "scheduled"
    assert captured_events[0].event_type == "failed"
    assert captured_events[0].event_phase == "failed"
    assert captured_events[0].event_status == "failed"
    assert captured_events[0].message == "lease_expired"
    assert captured_events[0].payload["failure_count"] == 1
    assert captured_events[0].payload["pending_video_count"] == 0


def test_complete_task_marks_job_succeeded_when_all_tasks_finish(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="leased",
            worker_id="worker-1",
            lease_until=now + timedelta(seconds=30),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    crawl_task_service.start_task(task_id=task_id, worker_id="worker-1", now=now)
    crawl_task_service.complete_task(task_id=task_id, worker_id="worker-1", now=now + timedelta(seconds=5))

    with Session(engine, expire_on_commit=False) as session:
        stored_job = session.get(CrawlJob, job_id)
        stored_task = session.get(CrawlTask, task_id)

    assert stored_task.status == "succeeded"
    assert stored_job.status == "succeeded"
    assert stored_job.started_at == now
    assert stored_job.finished_at == now + timedelta(seconds=5)


def test_complete_task_clears_stale_error_fields_after_retry_success(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="pornhub",
            priority="full",
            payload={},
            status="running",
            worker_id="worker-1",
            attempt=1,
            lease_until=now + timedelta(seconds=30),
            last_error="StageExecutionError: Critical stage 'extraction' failed",
            last_error_type="ValueError",
            started_at=now - timedelta(seconds=30),
        )
        session.add(task)
        session.commit()
        task_id = task.id

    crawl_task_service.complete_task(task_id=task_id, worker_id="worker-1", now=now)

    with Session(engine, expire_on_commit=False) as session:
        stored_task = session.get(CrawlTask, task_id)

    assert stored_task.status == "succeeded"
    assert stored_task.last_error is None
    assert stored_task.last_error_type is None


def test_recover_expired_dead_task_marks_job_failed(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="running",
            worker_id="worker-1",
            attempt=2,
            max_attempts=3,
            started_at=now - timedelta(minutes=1),
            lease_until=now - timedelta(seconds=1),
        )
        session.add(task)
        session.commit()

    crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=45)

    with Session(engine, expire_on_commit=False) as session:
        stored_job = session.get(CrawlJob, job_id)

    assert stored_job.status == "failed"
    assert stored_job.finished_at == now


def test_cancel_task_marks_job_cancelled_when_all_tasks_cancelled(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="pending",
            next_run_at=now,
        )
        session.add(task)
        session.commit()
        task_id = task.id

    crawl_task_service.cancel_task(task_id=task_id, now=now, reason="manual_cancel")

    with Session(engine, expire_on_commit=False) as session:
        stored_job = session.get(CrawlJob, job_id)
        stored_task = session.get(CrawlTask, task_id)

    assert stored_task.status == "cancelled"
    assert stored_task.last_error == "manual_cancel"
    assert stored_job.status == "cancelled"
    assert stored_job.finished_at == now


def test_replay_dead_task_resets_task_and_job_to_pending(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        job = session.get(CrawlJob, job_id)
        job.status = "failed"
        job.started_at = now - timedelta(minutes=2)
        job.finished_at = now - timedelta(minutes=1)
        task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="dead",
            attempt=3,
            max_attempts=3,
            started_at=now - timedelta(minutes=2),
            finished_at=now - timedelta(minutes=1),
            last_error="boom",
        )
        session.add(task)
        session.commit()
        task_id = task.id

    crawl_task_service.replay_dead_task(task_id=task_id, now=now)

    with Session(engine, expire_on_commit=False) as session:
        stored_job = session.get(CrawlJob, job_id)
        stored_task = session.get(CrawlTask, task_id)

    assert stored_task.status == "pending"
    assert stored_task.attempt == 0
    assert stored_task.started_at is None
    assert stored_task.finished_at is None
    assert stored_task.last_error is None
    assert stored_job.status == "pending"
    assert stored_job.finished_at is None


def test_complete_and_dead_mix_marks_job_partial_failed(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    job_id = _create_job(engine)
    now = datetime(2026, 4, 1, 12, 0, 0)

    with Session(engine, expire_on_commit=False) as session:
        succeeded_task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="succeeded",
            started_at=now - timedelta(minutes=2),
            finished_at=now - timedelta(minutes=1),
        )
        dead_task = CrawlTask(
            job_id=job_id,
            task_type="video_extract",
            site="youtube",
            priority="normal",
            payload={},
            status="running",
            worker_id="worker-1",
            attempt=2,
            max_attempts=3,
            started_at=now - timedelta(minutes=2),
            lease_until=now - timedelta(seconds=1),
        )
        session.add_all([succeeded_task, dead_task])
        session.commit()

    crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=45)

    with Session(engine, expire_on_commit=False) as session:
        stored_job = session.get(CrawlJob, job_id)

    assert stored_job.status == "partial_failed"


def test_video_extract_task_lifecycle_updates_projection(monkeypatch):
    engine = _setup_test_env(monkeypatch)
    now = datetime(2026, 4, 1, 12, 0, 0)

    job, task = crawl_task_service.create_job_with_task(
        job_type="video_extract",
        source_type="scheduled",
        site="youtube.com",
        task_type="video_extract",
        subscription_id=10,
        payload={"sync_state_id": 501, "url": "https://example.com/watch?v=1"},
        next_run_at=now,
    )

    with Session(engine, expire_on_commit=False) as session:
        projection = session.query(VideoExtractionProjection).one()
        assert projection.subscription_id == 10
        assert projection.group_kind == "state"
        assert projection.group_value == "501"
        assert projection.display_status == "queued"
        assert projection.queued_task_count == 1
        assert projection.pending_video_count == 1

    claimed = crawl_task_service.claim_next_task(worker_id="worker-1", now=now, lease_seconds=60)
    assert claimed is not None
    crawl_task_service.start_task(task_id=task.id, worker_id="worker-1", now=now + timedelta(seconds=1))

    with Session(engine, expire_on_commit=False) as session:
        projection = session.query(VideoExtractionProjection).one()
        assert projection.display_status == "running"
        assert projection.running_task_count == 1
        assert projection.pending_video_count == 1

    crawl_task_service.complete_task(task_id=task.id, worker_id="worker-1", now=now + timedelta(seconds=5))

    with Session(engine, expire_on_commit=False) as session:
        projection = session.query(VideoExtractionProjection).one()
        job_row = session.get(CrawlJob, job.id)

    assert projection.sync_status == "success"
    assert projection.display_status == "healthy"
    assert projection.completed_task_count == 1
    assert projection.pending_video_count == 0
    assert job_row.status == "succeeded"
