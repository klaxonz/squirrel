from __future__ import annotations

from domains.subscription.application.services.core.update.command_events import SubscriptionSyncCommandEventPublisher
from domains.subscription.application.services.core.update.models import QueuedSync, SyncCommand


class SubscriptionSyncQueuePlanner:
    def __init__(self, sync_state_service, event_publisher: SubscriptionSyncCommandEventPublisher):
        self._sync_state_service = sync_state_service
        self._event_publisher = event_publisher

    def queue_sync_state(self, command: SyncCommand, *, domain: str, scheduled: bool) -> QueuedSync:
        state, state_status = self._sync_state_service.prepare_sync_state_for_enqueue(
            command.subscription_id,
            command.url,
            command.mode.value,
            scheduled=scheduled,
        )
        if not state:
            return QueuedSync(None, 'failed', None, None, 0)

        run_context, _emit_run_created = self._event_publisher.build_run_context(
            subscription_id=command.subscription_id,
            sync_state_id=state.id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            run_id=command.run_id,
        )

        if state_status == 'deferred':
            return QueuedSync(state.id, 'deferred', run_context, None, state.pending_video_count)
        if state_status in {'in_progress', 'queued'}:
            return QueuedSync(state.id, state_status, run_context, None, state.pending_video_count)

        queue_token = self._sync_state_service.build_queue_token()
        queued_state = self._sync_state_service.queue_sync_state(state.id, queue_token)
        if not queued_state:
            return QueuedSync(state.id, 'failed', run_context, None, state.pending_video_count)
        if queued_state.queue_token != queue_token:
            status = 'in_progress' if queued_state.sync_status == 'running' else 'queued'
            return QueuedSync(queued_state.id, status, run_context, None, queued_state.pending_video_count)
        if queued_state.sync_status != 'queued':
            return QueuedSync(queued_state.id, 'failed', run_context, None, queued_state.pending_video_count)
        return QueuedSync(queued_state.id, 'ready', run_context, queue_token, queued_state.pending_video_count)
