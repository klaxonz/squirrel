from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_state import SubscriptionSyncState
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncPhase, SyncRunStatus, create_run


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
    run_projection = _get_latest_state_run_projection(session, state)
    if run_projection:
        _append_state_event(
            session,
            state=state,
            run_id=run_projection.run_id,
            request_id=run_projection.request_id,
            trace_id=run_projection.trace_id,
            trigger=run_projection.trigger or "system",
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
        )
        return

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
    run_projection = _get_latest_state_run_projection(session, state)
    if run_projection:
        started_at = run_projection.started_at or state.locked_at or state.last_sync_at
        _append_state_event(
            session,
            state=state,
            run_id=run_projection.run_id,
            request_id=run_projection.request_id,
            trace_id=run_projection.trace_id,
            trigger=run_projection.trigger or "system",
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
        )
        return

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


def _get_latest_state_run_projection(
    session: Session,
    state: SubscriptionSyncState,
) -> SubscriptionSyncRunProjection | None:
    try:
        return session.execute(
            select(SubscriptionSyncRunProjection)
            .join(
                SubscriptionSyncSubscriptionProjection,
                SubscriptionSyncSubscriptionProjection.latest_run_id == SubscriptionSyncRunProjection.run_id,
            )
            .where(
                SubscriptionSyncSubscriptionProjection.subscription_id == state.subscription_id,
                SubscriptionSyncRunProjection.sync_state_id == state.id,
            )
            .limit(1),
        ).scalar_one_or_none()
    except SQLAlchemyError:
        return None

