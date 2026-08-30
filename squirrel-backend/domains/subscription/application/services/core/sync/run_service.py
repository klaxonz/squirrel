from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from domains.subscription.domain.models.subscription_sync_run import SubscriptionSyncRun, SyncRunStatus
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
    """Owns the durable ledger for logical subscription-sync runs."""

    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

    @staticmethod
    def build_run_id() -> str:
        return uuid4().hex

    def create_run(
        self,
        subscription_id: int,
        sync_state_id: int | None,
        site: str | None,
        sync_mode: str,
        trigger: str | None,
        request_id: str | None = None,
        trace_id: str | None = None,
        *,
        run_id: str | None = None,
        status: str = SyncRunStatus.QUEUED.value,
        queue_token: str | None = None,
        cursor_in: dict | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        occurred_at: datetime | None = None,
    ) -> SyncRunContext:
        with self.session_factory() as session:
            return self.create_run_in_session(
                session,
                subscription_id=subscription_id,
                sync_state_id=sync_state_id,
                site=site,
                sync_mode=sync_mode,
                trigger=trigger,
                request_id=request_id,
                trace_id=trace_id,
                run_id=run_id,
                status=status,
                queue_token=queue_token,
                cursor_in=cursor_in,
                error_message=error_message,
                error_type=error_type,
                occurred_at=occurred_at,
            )

    def create_run_in_session(
        self,
        session: Session,
        *,
        subscription_id: int,
        sync_state_id: int | None,
        site: str | None,
        sync_mode: str,
        trigger: str | None,
        request_id: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
        status: str = SyncRunStatus.QUEUED.value,
        queue_token: str | None = None,
        cursor_in: dict | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        occurred_at: datetime | None = None,
    ) -> SyncRunContext:
        resolved_run_id = run_id or self.build_run_id()
        existing = session.get(SubscriptionSyncRun, resolved_run_id)
        if existing:
            self._validate_identity(existing, subscription_id, sync_state_id, sync_mode)
            if existing.status in self._terminal_statuses() and status not in self._terminal_statuses():
                raise ValueError(f'Terminal sync run cannot be reused: run_id={resolved_run_id}')
            return self._to_context(existing)

        created_at = occurred_at or datetime.now()
        run = SubscriptionSyncRun(
            id=resolved_run_id,
            subscription_id=subscription_id,
            sync_state_id=sync_state_id,
            site=(site or '').strip(),
            sync_mode=sync_mode,
            trigger=trigger,
            status=status,
            queue_token=queue_token,
            request_id=request_id,
            trace_id=trace_id,
            cursor_in=cursor_in,
            last_error=error_message,
            last_error_type=error_type,
            created_at=created_at,
            updated_at=created_at,
            finished_at=created_at if status in self._terminal_statuses() else None,
        )
        session.add(run)
        session.flush()
        return self._to_context(run)

    @staticmethod
    def mark_status_in_session(
        session: Session,
        run_id: str | None,
        status: str,
        *,
        queue_token: str | None = None,
        cursor_out: dict | None = None,
        videos_found: int | None = None,
        videos_enqueued: int | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        now: datetime | None = None,
    ) -> SubscriptionSyncRun | None:
        if not run_id:
            return None
        run = session.get(SubscriptionSyncRun, run_id)
        if not run:
            return None
        current_time = now or datetime.now()
        run.status = status
        run.updated_at = current_time
        if queue_token is not None:
            run.queue_token = queue_token
        if cursor_out is not None:
            run.cursor_out = cursor_out
        if videos_found is not None:
            run.videos_found += max(0, int(videos_found))
        if videos_enqueued is not None:
            run.videos_enqueued += max(0, int(videos_enqueued))
        run.last_error = error_message
        run.last_error_type = error_type
        if status == SyncRunStatus.RUNNING.value:
            run.started_at = run.started_at or current_time
            run.finished_at = None
        elif status in SubscriptionSyncRunService._terminal_statuses():
            run.finished_at = current_time
        return run

    @staticmethod
    def _terminal_statuses() -> set[str]:
        return {
            SyncRunStatus.SUCCEEDED.value,
            SyncRunStatus.FAILED.value,
            SyncRunStatus.DEFERRED.value,
            SyncRunStatus.CANCELLED.value,
        }

    @staticmethod
    def _validate_identity(
        run: SubscriptionSyncRun,
        subscription_id: int,
        sync_state_id: int | None,
        sync_mode: str,
    ) -> None:
        if run.subscription_id != subscription_id or run.sync_mode != sync_mode:
            raise ValueError(f'Sync run identity mismatch: run_id={run.id}')
        if sync_state_id is not None and run.sync_state_id not in {None, sync_state_id}:
            raise ValueError(f'Sync run state mismatch: run_id={run.id}')
        if run.sync_state_id is None and sync_state_id is not None:
            run.sync_state_id = sync_state_id

    @staticmethod
    def _to_context(run: SubscriptionSyncRun) -> SyncRunContext:
        return SyncRunContext(
            run_id=run.id,
            stream_id=run.id,
            subscription_id=run.subscription_id,
            sync_state_id=run.sync_state_id,
            site=run.site,
            sync_mode=run.sync_mode,
            trigger=run.trigger,
            request_id=run.request_id,
            trace_id=run.trace_id,
            created_at=run.created_at,
        )
mark_run_status_in_session = SubscriptionSyncRunService.mark_status_in_session
