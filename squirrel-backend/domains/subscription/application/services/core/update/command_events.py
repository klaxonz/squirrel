from __future__ import annotations

from domains.subscription.application.services.core.sync.run_service import SubscriptionSyncRunService, SyncRunContext
from domains.subscription.application.services.core.update.models import SyncCommand
from domains.subscription.domain.models.subscription_sync_run import SyncRunStatus
from infrastructure.database.session import get_session


class SubscriptionSyncCommandEventPublisher:
    """Creates durable run-ledger entries for sync commands."""

    def __init__(self, run_service: SubscriptionSyncRunService | None = None):
        self._run_service = run_service or SubscriptionSyncRunService(session_factory=get_session)

    def build_run_context(
        self,
        *,
        subscription_id: int,
        sync_state_id: int | None,
        site: str | None,
        sync_mode: str,
        trigger: str,
        trace_id: str | None,
        run_id: str | None,
        session=None,
        status: str = SyncRunStatus.QUEUED.value,
        queue_token: str | None = None,
        cursor_in: dict | None = None,
        error_message: str | None = None,
    ) -> tuple[SyncRunContext, bool]:
        created = not bool(run_id)
        kwargs = {
            'subscription_id': subscription_id,
            'sync_state_id': sync_state_id,
            'site': site,
            'sync_mode': sync_mode,
            'trigger': trigger,
            'trace_id': trace_id,
            'run_id': run_id,
            'status': status,
            'queue_token': queue_token,
            'cursor_in': cursor_in,
            'error_message': error_message,
        }
        if session is not None:
            context = self._run_service.create_run_in_session(session, **kwargs)
        else:
            context = self._run_service.create_run(**kwargs)
        return context, created

    def emit_deferred_event(
        self,
        command: SyncCommand,
        sync_state_id: int | None,
        site: str | None,
        reason: str,
    ) -> SyncRunContext:
        context, _ = self.build_run_context(
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=site,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            run_id=command.run_id,
            status=SyncRunStatus.DEFERRED.value,
            error_message=reason,
        )
        return context
