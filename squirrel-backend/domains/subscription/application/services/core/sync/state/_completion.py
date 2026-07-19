from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.sync.run_service import mark_run_status_in_session
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_run import SyncRunStatus
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncStatus

from ._completion_transitions import (
    complete_success_state,
    continue_full_batch_state,
    defer_state,
    mark_failed_state,
    mark_feed_completed_with_pending_state,
    mark_skipped_state,
    update_cursor,
)
from ._ownership import has_live_execution_token
from .session import get_session

ACTIVE_VIDEO_STATUSES = {
    CrawlTaskStatus.PENDING.value,
    CrawlTaskStatus.LEASED.value,
    CrawlTaskStatus.RUNNING.value,
    CrawlTaskStatus.RETRY_WAIT.value,
}
FAILED_VIDEO_STATUSES = {CrawlTaskStatus.DEAD.value, CrawlTaskStatus.CANCELLED.value}


def _complete_sync_success_in_session(
    session: Session,
    *,
    state: SubscriptionSyncState,
    run_id: str | None = None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    next_sync_at: datetime | None = None,
) -> SubscriptionSyncState:
    resolved_run_id = run_id or state.current_run_id
    now = datetime.now()
    complete_success_state(
        state,
        now=now,
        videos_found=videos_found,
        next_sync_at=next_sync_at,
    )
    state.current_run_id = None
    mark_run_status_in_session(
        session,
        resolved_run_id,
        SyncRunStatus.SUCCEEDED.value,
        cursor_out=state.cursor_payload,
        videos_found=videos_found,
        videos_enqueued=videos_enqueued,
        now=now,
    )
    return state


def continue_full_sync_batch(
    sync_state_id: int,
    *,
    cursor_payload: dict | None,
    latest_video_url: str | None,
    videos_found: int = 0,
    run_id: str | None = None,
    queue_token: str | None = None,
    execution_token: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = _get_owned_state(session, sync_state_id, run_id, queue_token, execution_token)
        if not state:
            return None

        continue_full_batch_state(
            state,
            now=now,
            cursor_payload=cursor_payload,
            latest_video_url=latest_video_url,
        )
        # The caller queues the continuation before this transaction commits. Keep ownership
        # with the same run even though the page-level queue token is rotated.
        state.current_run_id = run_id or state.current_run_id
        mark_run_status_in_session(
            session,
            state.current_run_id,
            SyncRunStatus.RUNNING.value,
            cursor_out=cursor_payload,
            videos_found=videos_found,
            now=now,
        )
        return state


def mark_sync_success(
    sync_state_id: int,
    *,
    cursor_payload: dict | None,
    latest_video_url: str | None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    next_sync_at: datetime | None = None,
    run_id: str | None = None,
    queue_token: str | None = None,
    execution_token: str | None = None,
    total_available: int | None = None,
) -> SubscriptionSyncState | None:
    with get_session() as session:
        state = _get_owned_state(session, sync_state_id, run_id, queue_token, execution_token)
        if not state:
            return None

        if state.sync_mode == 'full' and total_available is not None:
            subscription = session.get(Subscription, state.subscription_id)
            if subscription is not None:
                subscription.total_videos = max(0, int(total_available))

        active_count, failed_count, last_error = _video_task_summary(session, sync_state_id, run_id)
        state.pending_video_count = active_count
        now = datetime.now()

        if active_count > 0:
            mark_feed_completed_with_pending_state(
                state,
                now=now,
                cursor_payload=cursor_payload,
                latest_video_url=latest_video_url,
            )
            mark_run_status_in_session(
                session,
                run_id or state.current_run_id,
                SyncRunStatus.WAITING_VIDEOS.value,
                cursor_out=cursor_payload,
                videos_found=videos_found,
                videos_enqueued=videos_enqueued,
                now=now,
            )
            return state

        if failed_count > 0:
            resolved_run_id = run_id or state.current_run_id
            mark_failed_state(state, now=now, error_message=last_error or 'video_extract_failed')
            state.current_run_id = None
            mark_run_status_in_session(
                session,
                resolved_run_id,
                SyncRunStatus.FAILED.value,
                error_message=state.last_error,
                error_type='video_extract_failed',
                cursor_out=cursor_payload,
                videos_found=videos_found,
                videos_enqueued=videos_enqueued,
                now=now,
            )
            return state

        update_cursor(state, cursor_payload=cursor_payload, latest_video_url=latest_video_url)
        return _complete_sync_success_in_session(
            session,
            state=state,
            run_id=run_id,
            videos_found=videos_found,
            videos_enqueued=videos_enqueued,
            next_sync_at=next_sync_at,
        )


def mark_sync_skipped(
    sync_state_id: int,
    *,
    next_sync_at: datetime | None = None,
    reason: str | None = None,
    run_id: str | None = None,
    queue_token: str | None = None,
    execution_token: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = _get_owned_state(session, sync_state_id, run_id, queue_token, execution_token)
        if not state:
            return None
        resolved_run_id = run_id or state.current_run_id
        mark_skipped_state(state, now=now, next_sync_at=next_sync_at)
        state.last_error = reason
        state.current_run_id = None
        mark_run_status_in_session(
            session,
            resolved_run_id,
            SyncRunStatus.SUCCEEDED.value,
            error_message=reason,
            now=now,
        )
        return state


def mark_sync_failed(
    sync_state_id: int,
    error_message: str,
    *,
    error_type: str | None = None,
    run_id: str | None = None,
    queue_token: str | None = None,
    execution_token: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = _get_owned_state(session, sync_state_id, run_id, queue_token, execution_token)
        if not state:
            return None
        resolved_run_id = run_id or state.current_run_id
        mark_failed_state(state, now=now, error_message=error_message)
        state.current_run_id = None
        mark_run_status_in_session(
            session,
            resolved_run_id,
            SyncRunStatus.FAILED.value,
            error_message=error_message,
            error_type=error_type,
            now=now,
        )
        return state


def defer_sync_state(
    sync_state_id: int,
    *,
    delay: timedelta,
    error_message: str | None = None,
    run_id: str | None = None,
    queue_token: str | None = None,
    execution_token: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = _get_owned_state(session, sync_state_id, run_id, queue_token, execution_token)
        if not state:
            return None
        resolved_run_id = run_id or state.current_run_id
        defer_state(state, now=now, delay=delay, error_message=error_message)
        state.current_run_id = None
        mark_run_status_in_session(
            session,
            resolved_run_id,
            SyncRunStatus.DEFERRED.value,
            error_message=error_message,
            now=now,
        )
        return state


def decrement_pending_video_count(
    sync_state_id: int | None,
    count: int = 1,
    *,
    allow_completion: bool = True,
    run_id: str | None = None,
    execution_token: str | None = None,
) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = _get_owned_state(
            session,
            sync_state_id,
            run_id,
            None,
            execution_token,
            require_execution_ownership=bool(execution_token),
        )
        if not state:
            return
        active_count, failed_count, last_error = _video_task_summary(session, sync_state_id, run_id)
        state.pending_video_count = active_count
        state.version += 1
        if not allow_completion or active_count > 0 or state.sync_status != SyncStatus.RUNNING.value or state.locked_at:
            return

        resolved_run_id = run_id or state.current_run_id
        if failed_count > 0:
            now = datetime.now()
            mark_failed_state(state, now=now, error_message=last_error or 'video_extract_failed')
            state.current_run_id = None
            mark_run_status_in_session(
                session,
                resolved_run_id,
                SyncRunStatus.FAILED.value,
                error_message=state.last_error,
                error_type='video_extract_failed',
                now=now,
            )
            return
        _complete_sync_success_in_session(session, state=state, run_id=resolved_run_id)


def _get_owned_state(
    session: Session,
    sync_state_id: int,
    run_id: str | None,
    queue_token: str | None,
    execution_token: str | None,
    *,
    require_execution_ownership: bool = True,
) -> SubscriptionSyncState | None:
    state = session.execute(
        select(SubscriptionSyncState)
        .where(SubscriptionSyncState.id == sync_state_id)
        .with_for_update(),
    ).scalar_one_or_none()
    if not state:
        return None
    if state.current_run_id is not None and state.current_run_id != run_id:
        return None
    if run_id is not None and state.current_run_id != run_id:
        return None
    if require_execution_ownership and state.queue_token is not None and state.queue_token != queue_token:
        return None
    if queue_token is not None and state.queue_token != queue_token:
        return None
    if require_execution_ownership and (state.current_run_id is not None or state.execution_token is not None):
        if not has_live_execution_token(session, state, execution_token):
            return None
    elif execution_token is not None and state.execution_token != execution_token:
        return None
    return state


def _video_task_summary(
    session: Session,
    sync_state_id: int,
    run_id: str | None,
) -> tuple[int, int, str | None]:
    filters = [
        CrawlTask.task_type == 'video_extract',
        CrawlTask.sync_state_id == sync_state_id,
    ]
    if run_id:
        filters.append(CrawlTask.run_id == run_id)
    active_count, failed_count = session.execute(
        select(
            func.sum(case((CrawlTask.status.in_(ACTIVE_VIDEO_STATUSES), 1), else_=0)),
            func.sum(case((CrawlTask.status.in_(FAILED_VIDEO_STATUSES), 1), else_=0)),
        ).where(*filters),
    ).one()
    last_error = session.execute(
        select(func.coalesce(CrawlTask.last_error, CrawlTask.last_error_type))
        .where(*filters, CrawlTask.status.in_(FAILED_VIDEO_STATUSES))
        .order_by(CrawlTask.updated_at.desc(), CrawlTask.id.desc())
        .limit(1),
    ).scalar_one_or_none()
    return int(active_count or 0), int(failed_count or 0), last_error
