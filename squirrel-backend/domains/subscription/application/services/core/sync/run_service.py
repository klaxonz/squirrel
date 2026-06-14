from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select, text

from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from infrastructure.database.session import get_session


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
    sync_state_id: int | None
    site: str
    sync_mode: str
    trigger: str | None
    request_id: str | None
    trace_id: str | None
    created_at: datetime


class SubscriptionSyncRunService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

    @staticmethod
    def build_run_id() -> str:
        return uuid4().hex

    @staticmethod
    def create_run(
        subscription_id: int,
        sync_state_id: int | None,
        site: str | None,
        sync_mode: str,
        trigger: str | None,
        request_id: str | None = None,
        trace_id: str | None = None,
        *,
        occurred_at: datetime | None = None,
    ) -> SyncRunContext:
        run_id = SubscriptionSyncRunService.build_run_id()
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

    def next_seq_no(self, stream_id: str, *, session=None) -> int:
        if session is not None:
            session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:stream_id))"), {'stream_id': stream_id})
            value = session.execute(
                select(func.max(SubscriptionSyncEvent.seq_no)).where(SubscriptionSyncEvent.stream_id == stream_id),
            ).scalar_one_or_none()
            return int(value or 0) + 1

        with self.session_factory() as managed_session:
            managed_session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:stream_id))"), {'stream_id': stream_id})
            value = managed_session.execute(
                select(func.max(SubscriptionSyncEvent.seq_no)).where(SubscriptionSyncEvent.stream_id == stream_id),
            ).scalar_one_or_none()
            return int(value or 0) + 1


subscription_sync_run_service = SubscriptionSyncRunService()
build_run_id = subscription_sync_run_service.build_run_id
create_run = subscription_sync_run_service.create_run
next_seq_no = subscription_sync_run_service.next_seq_no
