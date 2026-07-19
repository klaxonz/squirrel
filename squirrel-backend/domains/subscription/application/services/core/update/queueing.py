from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select

from domains.subscription.application.services.core.update.command_events import SubscriptionSyncCommandEventPublisher
from domains.subscription.application.services.core.update.models import QueuedSync, SyncCommand
from domains.subscription.application.services.crawl.tasks.dispatch_scope import ensure_dispatch_scope
from domains.subscription.domain.models.crawl_dispatch_scope import CrawlDispatchScope
from domains.subscription.domain.models.subscription_sync_run import SyncRunStatus
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from infrastructure.config.settings import settings

FULL_SYNC_BUDGET_RETRY_DELAY = timedelta(minutes=5)


class SubscriptionSyncQueuePlanner:
    def __init__(self, sync_state_service, event_publisher: SubscriptionSyncCommandEventPublisher):
        self._sync_state_service = sync_state_service
        self._event_publisher = event_publisher

    @staticmethod
    def _has_full_sync_budget(session, domain: str) -> bool:
        global_key = 'full:global'
        site_key = f'full:site:{domain or "unknown"}'
        ensure_dispatch_scope(session, scope_type='sync_budget', scope_key=global_key)
        ensure_dispatch_scope(session, scope_type='sync_budget', scope_key=site_key)
        session.execute(
            select(CrawlDispatchScope)
            .where(
                CrawlDispatchScope.scope_type == 'sync_budget',
                CrawlDispatchScope.scope_key.in_([global_key, site_key]),
            )
            .order_by(CrawlDispatchScope.scope_key.asc())
            .with_for_update(),
        ).scalars().all()

        global_inflight = int(
            session.execute(
                select(func.count(SubscriptionSyncState.id)).where(
                    SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                    SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
                ),
            ).scalar_one()
            or 0
        )
        if global_inflight >= max(1, int(settings.FULL_SYNC_MAX_INFLIGHT)):
            return False

        site_inflight = int(
            session.execute(
                select(func.count(SubscriptionSyncState.id)).where(
                    SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                    SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
                    SubscriptionSyncState.site == domain
                    if domain
                    else SubscriptionSyncState.site.is_(None),
                ),
            ).scalar_one()
            or 0
        )
        return site_inflight < max(1, int(settings.FULL_SYNC_SITE_MAX_INFLIGHT))

    def queue_sync_state_in_session(self, session, command: SyncCommand, *, domain: str, scheduled: bool) -> QueuedSync:
        state, state_status = self._sync_state_service.prepare_sync_state_for_enqueue_in_session(
            session,
            command.subscription_id,
            command.url,
            command.mode.value,
            scheduled=scheduled,
        )
        if not state:
            return QueuedSync(None, 'failed', None, None, 0)
        if state_status in {'in_progress', 'queued'}:
            context = self._existing_run_context(command, state, domain, session=session)
            return QueuedSync(state.id, state_status, context, state.queue_token, state.pending_video_count)
        if state_status == 'deferred':
            context, _ = self._event_publisher.build_run_context(
                subscription_id=command.subscription_id,
                sync_state_id=state.id,
                site=domain,
                sync_mode=command.mode.value,
                trigger=command.trigger.value,
                trace_id=command.trace_id,
                run_id=command.run_id,
                session=session,
                status=SyncRunStatus.DEFERRED.value,
                cursor_in=state.cursor_payload,
                error_message='queue_backpressure',
            )
            return QueuedSync(state.id, 'deferred', context, None, state.pending_video_count)

        if command.mode.value == SyncMode.FULL.value and not self._has_full_sync_budget(session, domain):
            now = datetime.now()
            state.last_error = 'full_sync_budget_exhausted'
            state.next_sync_at = now + FULL_SYNC_BUDGET_RETRY_DELAY
            state.version += 1
            context, _ = self._event_publisher.build_run_context(
                subscription_id=command.subscription_id,
                sync_state_id=state.id,
                site=domain,
                sync_mode=command.mode.value,
                trigger=command.trigger.value,
                trace_id=command.trace_id,
                run_id=command.run_id,
                session=session,
                status=SyncRunStatus.DEFERRED.value,
                cursor_in=state.cursor_payload,
                error_message=state.last_error,
            )
            return QueuedSync(state.id, 'deferred', context, None, state.pending_video_count)

        queue_token = self._sync_state_service.build_queue_token()
        context, _ = self._event_publisher.build_run_context(
            subscription_id=command.subscription_id,
            sync_state_id=state.id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            run_id=command.run_id,
            session=session,
            queue_token=queue_token,
            cursor_in=state.cursor_payload,
        )
        queued_state = self._sync_state_service.queue_sync_state_in_session(
            session,
            state.id,
            queue_token,
            context.run_id,
        )
        return self._result_from_queued_state(state, queued_state, context, queue_token)

    def _existing_run_context(self, command, state, domain, *, session=None):
        run_id = state.current_run_id or command.run_id
        if not run_id:
            return None
        context, _ = self._event_publisher.build_run_context(
            subscription_id=command.subscription_id,
            sync_state_id=state.id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            run_id=run_id,
            session=session,
            queue_token=state.queue_token,
            cursor_in=state.cursor_payload,
        )
        return context

    @staticmethod
    def _result_from_queued_state(state, queued_state, context, queue_token):
        if not queued_state:
            return QueuedSync(state.id, 'failed', context, None, state.pending_video_count)
        if queued_state.queue_token != queue_token or queued_state.current_run_id != context.run_id:
            status = 'in_progress' if queued_state.sync_status == 'running' else 'queued'
            return QueuedSync(queued_state.id, status, context, None, queued_state.pending_video_count)
        if queued_state.sync_status != 'queued':
            return QueuedSync(queued_state.id, 'failed', context, None, queued_state.pending_video_count)
        return QueuedSync(queued_state.id, 'ready', context, queue_token, queued_state.pending_video_count)
