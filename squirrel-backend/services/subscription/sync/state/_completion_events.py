from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.subscription_sync_state import SubscriptionSyncState
from services.subscription.sync.run_service import SyncEventType, SyncPhase, SyncRunStatus

from ._events import _append_state_event


def append_success_event(
    session: Session,
    *,
    state: SubscriptionSyncState,
    started_at: datetime | None,
    now: datetime,
    source_video_count: int | None,
    videos_found: int,
    videos_enqueued: int,
    run_id: str | None,
    request_id: str | None,
    trace_id: str | None,
    trigger: str | None,
) -> None:
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=SyncEventType.COMPLETED,
        event_phase=SyncPhase.COMPLETED,
        event_status=SyncRunStatus.SUCCESS,
        payload={
            'cursor_payload': state.cursor_payload,
            'latest_video_url': state.last_seen_video_url,
            'source_video_count': source_video_count,
            'videos_found': videos_found,
            'videos_enqueued': videos_enqueued,
            'pending_video_count': state.pending_video_count,
            'failure_count': state.failure_count,
            'next_sync_at': state.next_sync_at,
            'duration_ms': int((now - started_at).total_seconds() * 1000) if started_at else 0,
        },
        occurred_at=now,
    )


def append_continued_event(
    session: Session,
    *,
    state: SubscriptionSyncState,
    now: datetime,
    latest_video_url: str | None,
    source_video_count: int | None,
    videos_found: int,
    videos_enqueued: int,
    run_id: str | None,
    request_id: str | None,
    trace_id: str | None,
    trigger: str | None,
) -> None:
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=SyncEventType.CONTINUED,
        event_phase=SyncPhase.FINALIZING,
        event_status=SyncRunStatus.RUNNING,
        payload={
            'cursor_payload': state.cursor_payload,
            'latest_video_url': latest_video_url,
            'source_video_count': source_video_count,
            'videos_found_delta': videos_found,
            'videos_enqueued_delta': videos_enqueued,
            'pending_video_count': state.pending_video_count,
            'next_sync_at': state.next_sync_at,
            'has_more': True,
        },
        occurred_at=now,
    )


def append_feed_completed_event(
    session: Session,
    *,
    state: SubscriptionSyncState,
    now: datetime,
    source_video_count: int | None,
    videos_found: int,
    videos_enqueued: int,
    run_id: str | None,
    request_id: str | None,
    trace_id: str | None,
    trigger: str | None,
) -> None:
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=SyncEventType.PHASE_CHANGED,
        event_phase=SyncPhase.EXTRACTING,
        event_status=SyncRunStatus.RUNNING,
        payload={
            'cursor_payload': state.cursor_payload,
            'latest_video_url': state.last_seen_video_url,
            'source_video_count': source_video_count,
            'videos_found': videos_found,
            'videos_enqueued': videos_enqueued,
            'pending_video_count': state.pending_video_count,
            'feed_completed': True,
        },
        occurred_at=now,
    )


def append_skipped_event(
    session: Session,
    *,
    state: SubscriptionSyncState,
    now: datetime,
    reason: str | None,
    event_type: str,
    event_phase: str,
    event_status: str,
    run_id: str | None,
    request_id: str | None,
    trace_id: str | None,
    trigger: str | None,
) -> None:
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=event_type,
        event_phase=event_phase,
        event_status=event_status,
        payload={
            'reason': reason,
            'next_sync_at': state.next_sync_at,
            'pending_video_count': state.pending_video_count,
        },
        message=reason,
        occurred_at=now,
    )


def append_failed_event(
    session: Session,
    *,
    state: SubscriptionSyncState,
    started_at: datetime | None,
    now: datetime,
    error_message: str,
    error_type: str | None,
    run_id: str | None,
    request_id: str | None,
    trace_id: str | None,
    trigger: str | None,
) -> None:
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=SyncEventType.FAILED,
        event_phase=SyncPhase.FAILED,
        event_status=SyncRunStatus.FAILED,
        payload={
            'error_type': error_type or 'sync_failed',
            'error_message': error_message,
            'failure_count': state.failure_count,
            'pending_video_count': state.pending_video_count,
            'next_sync_at': state.next_sync_at,
            'duration_ms': int((now - started_at).total_seconds() * 1000) if started_at else 0,
        },
        message=error_message,
        occurred_at=now,
    )


def append_deferred_event(
    session: Session,
    *,
    state: SubscriptionSyncState,
    now: datetime,
    error_message: str | None,
    run_id: str | None,
    request_id: str | None,
    trace_id: str | None,
    trigger: str | None,
) -> None:
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=SyncEventType.DEFERRED,
        event_phase=SyncPhase.DEFERRED,
        event_status=SyncRunStatus.DEFERRED,
        payload={
            'error_message': error_message,
            'pending_video_count': state.pending_video_count,
            'next_sync_at': state.next_sync_at,
        },
        message=error_message,
        occurred_at=now,
    )
