from __future__ import annotations

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.subscription.application.services.core.update.models import (
    SubscriptionUpdateRequest,
    UpdateMode,
    parse_trigger,
)
from domains.subscription.application.services.core.update.orchestrator import SubscriptionOrchestrator
from domains.subscription.application.services.crawl.tasks.errors import (
    CrawlExecutionError,
    CrawlTaskNotFoundError,
    CrawlTaskStateError,
)
from domains.subscription.domain.models.crawl_task import CrawlTask


class CrawlExecutorService:
    def __init__(
        self,
        lifecycle: SubscriptionSyncLifecycle,
        orchestrator_service: SubscriptionOrchestrator,
        subscription_svc: SubscriptionCrudService,
    ):
        self._lifecycle = lifecycle
        self._orchestrator = orchestrator_service
        self._subscription_service = subscription_svc

    def execute_subscription_sync_payload(self, payload: dict):
        subscription_id = int(payload['subscription_id'])
        url = payload.get('url') or self._resolve_subscription_url(subscription_id)
        trigger = parse_trigger(payload.get('trigger'))
        mode = self._parse_mode(payload.get('mode'))
        sync_state_id = payload.get('sync_state_id')
        queue_token = payload.get('queue_token')
        request_id = payload.get('request_id')
        run_id = payload.get('run_id')
        execution_token = payload.get('execution_token')
        trace_id = payload.get('trace_id')
        has_payload_cursor = 'cursor_payload' in payload
        has_payload_last_seen = 'last_seen_video_url' in payload
        cursor_payload = payload.get('cursor_payload') if has_payload_cursor else None
        last_seen_video_url = payload.get('last_seen_video_url') if has_payload_last_seen else None

        if sync_state_id and queue_token:
            claim_kwargs = {
                'run_id': run_id,
                'request_id': request_id,
                'trace_id': trace_id,
                'trigger': trigger.value,
            }
            if execution_token is not None:
                claim_kwargs['execution_token'] = execution_token
            claimed_state = self._lifecycle.claim_sync(int(sync_state_id), queue_token, **claim_kwargs)
            if not claimed_state:
                raise CrawlTaskStateError(f'Failed to claim sync state: sync_state_id={sync_state_id}')
            if has_payload_cursor:
                cursor_payload = cursor_payload
            elif mode == UpdateMode.FULL:
                cursor_payload = None
            else:
                cursor_payload = claimed_state.cursor_payload
            last_seen_video_url = last_seen_video_url if has_payload_last_seen else claimed_state.last_seen_video_url

        request = SubscriptionUpdateRequest(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=payload.get('user_id'),
            force=bool(payload.get('force', False)),
            trace_id=trace_id,
            request_id=request_id,
            run_id=run_id,
            sync_state_id=sync_state_id,
            queue_token=queue_token,
            execution_token=execution_token,
            cursor_payload=cursor_payload,
            last_seen_video_url=last_seen_video_url,
            inline_video_extraction=bool(payload.get('inline_video_extraction', False)),
        )
        result = self._orchestrator.update(request)
        if not result.success:
            raise CrawlExecutionError(
                result.error_message or 'subscription_sync_failed',
                retryable=result.retryable,
                error_type=result.error_type or 'subscription_sync_failed',
                retry_after_seconds=result.retry_after_seconds,
            )
        return result

    def execute_subscription_sync_task(self, task: CrawlTask):
        return self.execute_subscription_sync_payload(
            {
                **(task.payload or {}),
                'crawl_task_id': task.id,
                'execution_token': task.lease_token,
            },
        )

    def _resolve_subscription_url(self, subscription_id: int) -> str:
        subscription = self._subscription_service.get_subscription_by_id(subscription_id)
        if not subscription or not subscription.url:
            raise CrawlTaskNotFoundError(f'Subscription URL not found: {subscription_id}')
        return subscription.url

    @staticmethod
    def _parse_mode(raw: str | None) -> UpdateMode:
        if str(raw).lower() == UpdateMode.FULL.value:
            return UpdateMode.FULL
        if str(raw).lower() == UpdateMode.INCREMENTAL.value:
            return UpdateMode.INCREMENTAL
