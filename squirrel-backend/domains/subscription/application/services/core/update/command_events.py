from __future__ import annotations

from datetime import datetime

from domains.subscription.application.services.core.sync.event_service import SyncEventInput, append_event
from domains.subscription.application.services.core.sync.run_service import (
    SyncEventType,
    SyncPhase,
    SyncRunContext,
    SyncRunStatus,
    create_run,
)
from domains.subscription.application.services.core.update.models import SyncCommand


class SubscriptionSyncCommandEventPublisher:
    @staticmethod
    def build_run_context(
        *,
        subscription_id: int,
        sync_state_id: int | None,
        site: str | None,
        sync_mode: str,
        trigger: str,
        trace_id: str,
        run_id: str | None,
    ) -> tuple[SyncRunContext, bool]:
        if run_id:
            now = datetime.now()
            return (
                SyncRunContext(
                    run_id=run_id,
                    stream_id=run_id,
                    subscription_id=subscription_id,
                    sync_state_id=sync_state_id,
                    site=(site or '').strip(),
                    sync_mode=sync_mode,
                    trigger=trigger,
                    request_id=None,
                    trace_id=trace_id,
                    created_at=now,
                ),
                False,
            )
        return (
            create_run(
                subscription_id=subscription_id,
                sync_state_id=sync_state_id,
                site=site,
                sync_mode=sync_mode,
                trigger=trigger,
                trace_id=trace_id,
            ),
            True,
        )

    def emit_deferred_event(
        self,
        command: SyncCommand,
        sync_state_id: int | None,
        domain: str | None,
        reason: str,
    ) -> SyncRunContext:
        run_context, emit_run_created = self.build_run_context(
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            run_id=command.run_id,
        )
        if emit_run_created:
            self.append_run_created(command, sync_state_id, domain, run_context, 0)
        self.append_deferred_event(command, sync_state_id, domain, run_context, reason, 0)
        return run_context

    @staticmethod
    def append_run_created(
        command: SyncCommand,
        sync_state_id: int | None,
        domain: str | None,
        run_context: SyncRunContext,
        pending_video_count: int,
    ) -> None:
        append_event(SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
            payload={'pending_video_count': pending_video_count},
            occurred_at=run_context.created_at,
        ))

    @staticmethod
    def append_queued_event(
        command: SyncCommand,
        *,
        sync_state_id: int,
        domain: str,
        queue_token: str,
        request_id: str,
        run_context: SyncRunContext,
        pending_video_count: int,
        direct: bool = False,
    ) -> None:
        payload = {
            'queue_token': queue_token,
            'pending_video_count': pending_video_count,
        }
        if direct:
            payload['direct'] = True
        append_event(SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            request_id=request_id,
            trace_id=command.trace_id,
            event_type=SyncEventType.QUEUED,
            event_phase=SyncPhase.QUEUED,
            event_status=SyncRunStatus.QUEUED,
            payload=payload,
        ))

    @staticmethod
    def append_deferred_event(
        command: SyncCommand,
        sync_state_id: int | None,
        domain: str | None,
        run_context: SyncRunContext,
        reason: str,
        pending_video_count: int,
    ) -> None:
        append_event(SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            event_type=SyncEventType.DEFERRED,
            event_phase=SyncPhase.DEFERRED,
            event_status=SyncRunStatus.DEFERRED,
            payload={
                'reason': reason,
                'pending_video_count': pending_video_count,
                'error_message': reason,
            },
        ))


subscription_sync_command_event_publisher = SubscriptionSyncCommandEventPublisher()
