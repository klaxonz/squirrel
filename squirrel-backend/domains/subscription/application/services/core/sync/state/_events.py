from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from domains.subscription.application.services.core.sync.event_service import SyncEventInput, append_event
from domains.subscription.application.services.core.sync.run_service import (
    SyncEventType,
    SyncPhase,
    SyncRunStatus,
    create_run,
)
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState


def _append_recovery_run_events(
    session: Session,
    *,
    state: SubscriptionSyncState,
    event_type: str,
    event_phase: str,
    event_status: str,
    reason: str,
    occurred_at: datetime,
) -> None:
    """Append recovery events on a fresh run.

    Previously this tried to attach the recovery event to the latest existing run projection for
    the state. With the run/subscription projection tables removed, recovery always opens a new
    system run and emits RUN_CREATED + the recovery event onto it.
    """
    run_context = create_run(
        subscription_id=state.subscription_id,
        sync_state_id=state.id,
        site=state.site,
        sync_mode=state.sync_mode,
        trigger="system",
        occurred_at=occurred_at,
    )
    append_event(
        SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger="system",
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
            payload={"pending_video_count": state.pending_video_count},
            occurred_at=occurred_at,
        ),
        session=session,
    )
    append_event(
        SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger="system",
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload={
                "reason": reason,
                "error_message": reason,
                "pending_video_count": state.pending_video_count,
                "next_sync_at": state.next_sync_at,
            },
            message=reason,
            occurred_at=occurred_at,
        ),
        session=session,
    )


def _append_terminal_reconcile_run_events(
    session: Session,
    *,
    state: SubscriptionSyncState,
    event_type: str,
    event_phase: str,
    event_status: str,
    reason: str,
    error_message: str | None,
    occurred_at: datetime,
) -> None:
    """Append terminal reconcile events on a fresh run.

    See ``_append_recovery_run_events`` for why this always opens a new run instead of reusing
    an existing run projection.
    """
    run_context = create_run(
        subscription_id=state.subscription_id,
        sync_state_id=state.id,
        site=state.site,
        sync_mode=state.sync_mode,
        trigger="system",
        occurred_at=occurred_at,
    )
    append_event(
        SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger="system",
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
            payload={"pending_video_count": state.pending_video_count},
            occurred_at=occurred_at,
        ),
        session=session,
    )

    started_at = state.locked_at or state.last_sync_at
    append_event(
        SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger="system",
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload={
                "reason": reason,
                "error_message": error_message,
                "failure_count": state.failure_count,
                "pending_video_count": state.pending_video_count,
                "next_sync_at": state.next_sync_at,
                "duration_ms": int((occurred_at - started_at).total_seconds() * 1000) if started_at else 0,
            },
            message=error_message or reason,
            occurred_at=occurred_at,
        ),
        session=session,
    )


def _append_state_event(
    session: Session,
    *,
    state: SubscriptionSyncState,
    run_id: str | None,
    request_id: str | None,
    trace_id: str | None,
    trigger: str | None,
    event_type: str,
    event_phase: str | None,
    event_status: str | None,
    payload: dict | None = None,
    message: str | None = None,
    occurred_at: datetime | None = None,
) -> None:
    if not run_id:
        return
    append_event(
        SyncEventInput(
            stream_id=run_id,
            subscription_id=state.subscription_id,
            sync_state_id=state.id,
            site=state.site,
            sync_mode=state.sync_mode,
            trigger=trigger,
            request_id=request_id,
            trace_id=trace_id,
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload=payload,
            message=message,
            occurred_at=occurred_at,
        ),
        session=session,
    )
