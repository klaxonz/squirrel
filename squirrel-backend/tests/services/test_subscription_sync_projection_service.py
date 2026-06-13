from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import services.subscription.sync.projection.store as projection_store
from models import Base
from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from models.subscription_sync_trend_projection import SubscriptionSyncTrendProjection
from services.subscription.sync.projection.service import SubscriptionSyncProjectionService
from services.subscription.sync.run_service import SyncEventType, SyncPhase, SyncRunStatus


def _build_event(
    *,
    stream_id: str = "run-full-1",
    seq_no: int,
    occurred_at: datetime,
    event_type: str,
    event_phase: str,
    event_status: str,
    payload: dict | None = None,
) -> SubscriptionSyncEvent:
    return SubscriptionSyncEvent(
        stream_id=stream_id,
        subscription_id=101,
        sync_state_id=1001,
        site="bilibili.com",
        sync_mode="full",
        trigger="manual",
        request_id="req-full-1",
        trace_id="trace-full-1",
        event_type=event_type,
        event_phase=event_phase,
        event_status=event_status,
        seq_no=seq_no,
        payload=payload or {},
        occurred_at=occurred_at,
        created_at=occurred_at,
    )


@pytest.fixture(autouse=True)
def _patch_advisory_lock():
    """Make PostgreSQL-specific advisory_lock a no-op for SQLite tests."""
    original = projection_store.advisory_lock
    projection_store.advisory_lock = lambda session, key: None
    yield
    projection_store.advisory_lock = original


@pytest.fixture
def svc():
    return SubscriptionSyncProjectionService()


def test_apply_events_keeps_run_counters_cumulative_across_full_sync_batches(svc):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncSubscriptionProjection.__table__,
            SubscriptionSyncTrendProjection.__table__,
        ],
    )

    started_at = datetime(2026, 4, 2, 12, 0, 0)
    events = [
        _build_event(
            seq_no=1,
            occurred_at=started_at,
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
            payload={"pending_video_count": 0},
        ),
        _build_event(
            seq_no=2,
            occurred_at=started_at + timedelta(seconds=1),
            event_type=SyncEventType.QUEUED,
            event_phase=SyncPhase.QUEUED,
            event_status=SyncRunStatus.QUEUED,
            payload={"pending_video_count": 0},
        ),
        _build_event(
            seq_no=3,
            occurred_at=started_at + timedelta(seconds=2),
            event_type=SyncEventType.CLAIMED,
            event_phase=SyncPhase.CLAIMED,
            event_status=SyncRunStatus.RUNNING,
            payload={"pending_video_count": 0},
        ),
        _build_event(
            seq_no=4,
            occurred_at=started_at + timedelta(seconds=3),
            event_type=SyncEventType.PHASE_CHANGED,
            event_phase=SyncPhase.CALCULATING_DELTA,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_found": 3},
        ),
        _build_event(
            seq_no=5,
            occurred_at=started_at + timedelta(seconds=4),
            event_type=SyncEventType.VIDEO_FOUND,
            event_phase=SyncPhase.CALCULATING_DELTA,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_found_delta": 3, "videos_found": 3},
        ),
        _build_event(
            seq_no=6,
            occurred_at=started_at + timedelta(seconds=5),
            event_type=SyncEventType.VIDEO_ENQUEUED,
            event_phase=SyncPhase.ENQUEUEING,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_enqueued_delta": 2, "videos_enqueued": 2},
        ),
        _build_event(
            seq_no=7,
            occurred_at=started_at + timedelta(seconds=6),
            event_type=SyncEventType.VIDEO_SKIPPED,
            event_phase=SyncPhase.ENQUEUEING,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_skipped_delta": 1, "videos_skipped": 1},
        ),
        _build_event(
            seq_no=8,
            occurred_at=started_at + timedelta(seconds=7),
            event_type=SyncEventType.CONTINUED,
            event_phase=SyncPhase.FINALIZING,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_found_delta": 3, "videos_enqueued_delta": 2, "has_more": True},
        ),
        _build_event(
            seq_no=9,
            occurred_at=started_at + timedelta(seconds=8),
            event_type=SyncEventType.PHASE_CHANGED,
            event_phase=SyncPhase.CALCULATING_DELTA,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_found": 4},
        ),
        _build_event(
            seq_no=10,
            occurred_at=started_at + timedelta(seconds=9),
            event_type=SyncEventType.VIDEO_FOUND,
            event_phase=SyncPhase.CALCULATING_DELTA,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_found_delta": 4, "videos_found": 4},
        ),
        _build_event(
            seq_no=11,
            occurred_at=started_at + timedelta(seconds=10),
            event_type=SyncEventType.VIDEO_ENQUEUED,
            event_phase=SyncPhase.ENQUEUEING,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_enqueued_delta": 3, "videos_enqueued": 3},
        ),
        _build_event(
            seq_no=12,
            occurred_at=started_at + timedelta(seconds=11),
            event_type=SyncEventType.VIDEO_SKIPPED,
            event_phase=SyncPhase.ENQUEUEING,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_skipped_delta": 1, "videos_skipped": 1},
        ),
        _build_event(
            seq_no=13,
            occurred_at=started_at + timedelta(seconds=12),
            event_type=SyncEventType.COMPLETED,
            event_phase=SyncPhase.COMPLETED,
            event_status=SyncRunStatus.SUCCESS,
            payload={"videos_found": 4, "videos_enqueued": 3, "pending_video_count": 0},
        ),
    ]

    with Session(engine, expire_on_commit=False) as session:
        svc.apply_events(events, session=session)
        run_projection = session.get(SubscriptionSyncRunProjection, "run-full-1")

    assert run_projection is not None
    assert run_projection.status == SyncRunStatus.SUCCESS
    assert run_projection.videos_found == 7
    assert run_projection.videos_enqueued == 5
    assert run_projection.videos_skipped == 2


def test_apply_subscription_projection_ignores_late_progress_from_previous_run(svc):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            SubscriptionSyncRunProjection.__table__,
            SubscriptionSyncSubscriptionProjection.__table__,
            SubscriptionSyncTrendProjection.__table__,
        ],
    )

    started_at = datetime(2026, 4, 2, 12, 0, 0)
    events = [
        _build_event(
            stream_id="run-old",
            seq_no=1,
            occurred_at=started_at,
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
        ),
        _build_event(
            stream_id="run-new",
            seq_no=1,
            occurred_at=started_at + timedelta(seconds=10),
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
        ),
        _build_event(
            stream_id="run-new",
            seq_no=2,
            occurred_at=started_at + timedelta(seconds=11),
            event_type=SyncEventType.PHASE_CHANGED,
            event_phase=SyncPhase.FETCHING_FEED,
            event_status=SyncRunStatus.RUNNING,
        ),
        _build_event(
            stream_id="run-old",
            seq_no=2,
            occurred_at=started_at + timedelta(seconds=12),
            event_type=SyncEventType.VIDEO_EXTRACTED,
            event_phase=SyncPhase.EXTRACTING,
            event_status=SyncRunStatus.RUNNING,
            payload={"videos_extracted_delta": 1},
        ),
    ]

    with Session(engine, expire_on_commit=False) as session:
        svc.apply_events(events, session=session)
        projection = session.get(SubscriptionSyncSubscriptionProjection, 101)

    assert projection is not None
    assert projection.latest_run_id == "run-new"
    assert projection.current_status == SyncRunStatus.RUNNING
    assert projection.current_phase == SyncPhase.FETCHING_FEED
