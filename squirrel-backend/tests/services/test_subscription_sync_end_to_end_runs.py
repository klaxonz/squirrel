from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState
from infrastructure.database.base import Base


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
                site='youtube.com',
                sync_mode='incremental',
                sync_status='running',
                cursor_payload={'cursor': 'done'},
                last_seen_video_url='https://example.com/video/1',
                last_sync_at=now - timedelta(minutes=1),
                last_success_at=None,
                next_sync_at=now + timedelta(minutes=5),
                queued_at=now - timedelta(minutes=2),
                locked_at=now - timedelta(minutes=2),
                queue_token='queue-token',
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
        cursor_payload={'cursor': 'done'},
        latest_video_url='https://example.com/video/1',
        videos_found=10,
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    # pending videos remain -> stays running, success not finalized
    assert state.sync_status == 'running'
    assert state.locked_at is None
    assert state.pending_video_count == 3
    assert state.last_success_at is None

    sss_svc.decrement_pending_video_count(
        11,
        count=3,
    )

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 11)

    assert state.sync_status == 'success'
    assert state.pending_video_count == 0
    assert state.last_success_at is not None


def test_record_gap_observation_returns_full_backfill_request_when_score_crosses_threshold(
    engine,
    session_factory,
    sss_session_patch,
):
    engine = _setup_state_env(engine)
    sss_svc = subscription_sync_state_service

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=21,
                subscription_id=7,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='success',
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url='https://example.com/video/anchor',
            ),
        )
        session.commit()

    summary = sss_svc.record_gap_observation(
        sync_state_id=21,
        head_sample_urls=['https://example.com/video/new-1', 'https://example.com/video/new-2'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=120,
        local_total=80,
        now=now,
    )

    assert summary['gap_suspicion_score'] >= 8
    assert summary['should_request_full'] is True
    assert summary['site'] == 'youtube.com'
    assert summary['sync_state_id'] == 21

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 21)

    assert state.gap_suspicion_score == summary['gap_suspicion_score']
    assert state.head_anchor_missing_count == 1
    assert state.last_full_requested_at is None

    sss_svc.mark_full_sync_requested(21, now=now)

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 21)

    assert state.last_full_requested_at == now


def test_lifecycle_record_gap_observation_enqueues_full_backfill_when_score_crosses_threshold(
    engine,
    session_factory,
    sss_session_patch,
):
    engine = _setup_state_env(engine)

    request_calls = []

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=22,
                subscription_id=8,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='success',
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url='https://example.com/video/anchor',
            ),
        )
        session.commit()

    from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
    from domains.subscription.application.services.core.update.models import (
        SubscriptionUpdateRequest,
        SubscriptionUpdateResult,
        UpdateMode,
        UpdateTrigger,
    )

    request = SubscriptionUpdateRequest(
        subscription_id=8,
        sync_state_id=22,
        url='https://www.youtube.com/channel/demo',
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        trace_id='trace-1',
    )
    result = SubscriptionUpdateResult(
        subscription_id=8,
        success=True,
        videos_found=2,
        videos_enqueued=2,
        head_sample_urls=['https://example.com/video/new-1', 'https://example.com/video/new-2'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=120,
    )

    lifecycle = SubscriptionSyncLifecycle(session_factory=session_factory)
    with (
        patch(
            'domains.subscription.application.services.core.sync.lifecycle.get_subscription_by_id',
            return_value=SimpleNamespace(total_videos=80),
        ),
        patch.object(
            SubscriptionSyncLifecycle,
            'request_sync',
            autospec=True,
            side_effect=lambda self, **kw: request_calls.append(kw) or SimpleNamespace(status='queued'),
        ),
    ):
        lifecycle.record_gap_observation(request, result)

    assert request_calls == [
        {
            'subscription_id': 8,
            'url': 'https://www.youtube.com/channel/demo',
            'trigger': UpdateTrigger.SCHEDULED,
            'mode': UpdateMode.FULL,
            'trace_id': 'trace-1',
        }
    ]

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 22)

    assert state.last_full_requested_at is not None


def test_lifecycle_record_gap_observation_skips_full_backfill_when_inflight_budget_exhausted(
    engine,
    session_factory,
    sss_session_patch,
):
    engine = _setup_state_env(engine)

    request_calls = []

    now = datetime(2026, 4, 4, 12, 0, 0)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            SubscriptionSyncState(
                id=23,
                subscription_id=9,
                site='youtube.com',
                sync_mode='incremental',
                sync_status='success',
                next_sync_at=now + timedelta(minutes=5),
                last_seen_video_url='https://example.com/video/anchor',
            ),
        )
        session.commit()

    from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
    from domains.subscription.application.services.core.update.models import (
        SubscriptionUpdateRequest,
        SubscriptionUpdateResult,
        UpdateMode,
        UpdateTrigger,
    )

    request = SubscriptionUpdateRequest(
        subscription_id=9,
        sync_state_id=23,
        url='https://www.youtube.com/channel/demo',
        trigger=UpdateTrigger.SCHEDULED,
        mode=UpdateMode.INCREMENTAL,
        trace_id='trace-2',
    )
    result = SubscriptionUpdateResult(
        subscription_id=9,
        success=True,
        videos_found=2,
        videos_enqueued=2,
        head_sample_urls=['https://example.com/video/new-1', 'https://example.com/video/new-2'],
        anchor_found=False,
        cursor_invalid=True,
        cursor_loop_detected=False,
        total_available=120,
    )

    lifecycle = SubscriptionSyncLifecycle(session_factory=session_factory)
    with (
        patch(
            'domains.subscription.application.services.core.sync.lifecycle.get_subscription_by_id',
            return_value=SimpleNamespace(total_videos=80),
        ),
        patch.object(SubscriptionSyncLifecycle, '_can_request_full_sync', return_value=False),
        patch.object(
            SubscriptionSyncLifecycle,
            'request_sync',
            autospec=True,
            side_effect=lambda self, **kw: request_calls.append(kw),
        ),
    ):
        lifecycle.record_gap_observation(request, result)

    assert request_calls == []

    with Session(engine, expire_on_commit=False) as session:
        state = session.get(SubscriptionSyncState, 23)

    assert state.last_full_requested_at is None
