from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, select, text

from core.database import get_session
from models.subscription_sync_event import SubscriptionSyncEvent


class SyncEventType:
    RUN_CREATED = 'run_created'
    QUEUED = 'queued'
    CLAIMED = 'claimed'
    STARTED = 'started'
    CONTINUED = 'continued'
    PHASE_CHANGED = 'phase_changed'
    PROGRESS_UPDATED = 'progress_updated'
    VIDEO_FOUND = 'video_found'
    VIDEO_ENQUEUED = 'video_enqueued'
    VIDEO_EXTRACTED = 'video_extracted'
    VIDEO_SKIPPED = 'video_skipped'
    DEFERRED = 'deferred'
    FAILED = 'failed'
    COMPLETED = 'completed'
    TIMEOUT_RECOVERED = 'timeout_recovered'
    STALE_QUEUED_RECOVERED = 'stale_queued_recovered'
    STALE_RUNNING_RECOVERED = 'stale_running_recovered'
    MANUAL_RECONCILE_TRIGGERED = 'manual_reconcile_triggered'


class SyncPhase:
    INIT = 'init'
    QUEUED = 'queued'
    CLAIMED = 'claimed'
    FETCHING_FEED = 'fetching_feed'
    CALCULATING_DELTA = 'calculating_delta'
    EXTRACTING = 'extracting'
    ENQUEUEING = 'enqueueing'
    FINALIZING = 'finalizing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    DEFERRED = 'deferred'


class SyncRunStatus:
    CREATED = 'created'
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    DEFERRED = 'deferred'
    TIMEOUT = 'timeout'


@dataclass(frozen=True)
class SyncRunContext:
    run_id: str
    stream_id: str
    subscription_id: int
    sync_state_id: Optional[int]
    site: str
    sync_mode: str
    trigger: Optional[str]
    request_id: Optional[str]
    trace_id: Optional[str]
    created_at: datetime


def build_run_id() -> str:
    return uuid4().hex


def create_run(
    subscription_id: int,
    sync_state_id: Optional[int],
    site: Optional[str],
    sync_mode: str,
    trigger: Optional[str],
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    *,
    occurred_at: Optional[datetime] = None,
) -> SyncRunContext:
    run_id = build_run_id()
    created_at = occurred_at or datetime.now()
    return SyncRunContext(
        run_id=run_id,
        stream_id=run_id,
        subscription_id=subscription_id,
        sync_state_id=sync_state_id,
        site=(site or '').strip(),
        sync_mode=sync_mode,
        trigger=trigger,
        request_id=request_id,
        trace_id=trace_id,
        created_at=created_at,
    )


def next_seq_no(stream_id: str, *, session=None) -> int:
    if session is not None:
        session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:stream_id))'), {'stream_id': stream_id})
        value = session.execute(
            select(func.max(SubscriptionSyncEvent.seq_no)).where(SubscriptionSyncEvent.stream_id == stream_id)
        ).scalar_one_or_none()
        return int(value or 0) + 1

    with get_session() as managed_session:
        managed_session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:stream_id))'), {'stream_id': stream_id})
        value = managed_session.execute(
            select(func.max(SubscriptionSyncEvent.seq_no)).where(SubscriptionSyncEvent.stream_id == stream_id)
        ).scalar_one_or_none()
        return int(value or 0) + 1
