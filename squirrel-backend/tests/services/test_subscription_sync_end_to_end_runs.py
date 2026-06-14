from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from shared_kernel.domain.base import Base


@pytest.fixture
def engine(engine):
    return engine


@pytest.fixture
def sss_session_patch(session_factory):
    """Redirect module-level services to use test session_factory."""
    from infrastructure.database import session as database

    with patch.object(database, 'get_session', session_factory):
        yield


def _setup_state_env(engine):
    Base.metadata.create_all(
        engine,
        tables=[
            SubscriptionSyncState.__table__,
        ],
    )
    return engine


def test_mark_sync_success_stays_running_until_pending_videos_are_drained(engine, session_factory, sss_session_patch):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service

    now = datetime(2026, 4, 2, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=11,
                subscription_id=1,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="running",
                cursor_payload={"cursor": "done"},
                last_seen_video_url="https://example.com/video/1",
                last_sync_at=now - timedelta(minutes=1),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=5),
                queued_at=now - timedelta(minutes=2),
                locked_at=now - timedelta(minutes=2),
                queue_token="queue-token",
                pending_video_count=3,
                failure_count=0,
                idle_sync_count=0,
                version=0,
                last_error=None,
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(minutes=2),
            ),
        )
        session.commit()

    sss_svc.mark_sync_success(
        11,
        cursor_payload={"cursor": "done"},
        latest_video_url="https://example.com/video/1",
        source_video_count=10,
        videos_found=10,
        videos_enqueued=8,
        run_id="run-1",
        request_id="req-1",
        trace_id="trace-1",
        trigger="manual",
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    # pending videos remain -> stays running, success not finalized
    assert state.sync_status == "running"
    assert state.locked_at is None
    assert state.pending_video_count == 3
    assert state.last_success_at is None

    sss_svc.decrement_pending_video_count(
        11,
        count=3,
        run_id="run-1",
        request_id="req-1",
        trace_id="trace-1",
        trigger="manual",
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    assert state.sync_status == "success"
    assert state.pending_video_count == 0
    assert state.last_success_at is not None


def test_record_gap_observation_enqueues_full_backfill_when_score_crosses_threshold(engine, session_factory, sss_session_patch):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service

    request_calls = []

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=21,
                subscription_id=7,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="success",
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url="https://example.com/video/anchor",
            ),
        )
        session.commit()

    from domains.subscription.application.services.core.sync.state import _gap as gap_module
    from domains.subscription.application.services.core.update.commands import SubscriptionSyncCommandService
    from domains.subscription.application.services.core.update.models import UpdateMode, UpdateTrigger

    with patch.object(gap_module, "_can_request_full_sync", return_value=True), \
         patch("domains.subscription.application.services.core.crud.get_subscription_by_id", return_value=None), \
         patch.object(SubscriptionSyncCommandService, "request_sync", lambda self, **kw: request_calls.append(kw)):
        summary = sss_svc.record_gap_observation(
            sync_state_id=21,
            head_sample_urls=["https://example.com/video/new-1", "https://example.com/video/new-2"],
            anchor_found=False,
            cursor_invalid=True,
            cursor_loop_detected=False,
            total_available=120,
            local_total=80,
            now=now,
            trigger="scheduled",
            trace_id="trace-1",
        )

    assert summary["gap_suspicion_score"] >= 8
    assert summary["emitted_full_request"] is True
    assert request_calls == [{
        "subscription_id": 7,
        "url": "",
        "trigger": UpdateTrigger.SCHEDULED,
        "mode": UpdateMode.FULL,
        "trace_id": "trace-1",
    }]

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 21)

    assert state.gap_suspicion_score == summary["gap_suspicion_score"]
    assert state.head_anchor_missing_count == 1
    assert state.last_full_requested_at == now


def test_record_gap_observation_skips_full_backfill_when_inflight_budget_exhausted(engine, session_factory, sss_session_patch):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service

    request_calls = []

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=22,
                subscription_id=8,
                site="youtube.com",
                sync_mode="incremental",
                sync_status="success",
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url="https://example.com/video/anchor",
            ),
        )
        session.commit()

    from domains.subscription.application.services.core.sync.state import _gap as gap_module
    from domains.subscription.application.services.core.update.commands import SubscriptionSyncCommandService

    with patch.object(gap_module, "_can_request_full_sync", return_value=False), \
         patch.object(SubscriptionSyncCommandService, "request_sync", lambda self, **kw: request_calls.append(kw)):
        summary = sss_svc.record_gap_observation(
            sync_state_id=22,
            head_sample_urls=["https://example.com/video/new-1", "https://example.com/video/new-2"],
            anchor_found=False,
            cursor_invalid=True,
            cursor_loop_detected=False,
            total_available=120,
            local_total=80,
            now=now,
        )

    assert summary["gap_suspicion_score"] >= 8
    # score crossed and last_full_requested_at still stamped, but request skipped due to inflight budget
    assert summary["emitted_full_request"] is False
    assert request_calls == []

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 22)

    assert state.last_full_requested_at == now
