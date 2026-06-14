from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from infrastructure.database.session import get_session


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
    """Allocates ``run_id`` correlation identifiers for subscription sync runs.

    The append-only ``subscription_sync_event`` table and its sequence allocator were removed;
    ``run_id`` survives as a pure correlation ID threaded through CrawlTask payloads, API
    responses, and the task-progress path. ``create_run`` only builds an in-memory context.
    """

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


subscription_sync_run_service = SubscriptionSyncRunService()
build_run_id = subscription_sync_run_service.build_run_id
create_run = subscription_sync_run_service.create_run
