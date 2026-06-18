from __future__ import annotations

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
from domains.subscription.application.services.core.crud import subscription_crud_service
from domains.subscription.application.services.core.update.models import (
    SubscriptionUpdateRequest,
    UpdateMode,
    parse_trigger,
)
from domains.subscription.application.services.core.update.orchestrator import orchestrator
from domains.subscription.domain.models.crawl_task import CrawlTask


class CrawlExecutorService:
    def __init__(
        self,
        sync_state_service=None,
        orchestrator_service=None,
        subscription_svc=None,
    ):
        self._sync_state_service = sync_state_service or subscription_sync_state_service
        self._orchestrator = orchestrator_service or orchestrator
        self._subscription_service = subscription_svc or subscription_crud_service

    def execute_subscription_sync_payload(self, payload: dict):
        subscription_id = int(payload["subscription_id"])
        url = payload.get("url") or self._resolve_subscription_url(subscription_id)
        trigger = parse_trigger(payload.get("trigger"))
        mode = self._parse_mode(payload.get("mode"))
        sync_state_id = payload.get("sync_state_id")
        queue_token = payload.get("queue_token")
        request_id = payload.get("request_id")
        run_id = payload.get("run_id")
        trace_id = payload.get("trace_id")
        cursor_payload = payload.get("cursor_payload")
        last_seen_video_url = payload.get("last_seen_video_url")

        if sync_state_id and queue_token:
            claimed_state = self._sync_state_service.claim_sync_state(
                int(sync_state_id),
                queue_token,
                run_id=run_id,
                request_id=request_id,
                trace_id=trace_id,
                trigger=trigger.value,
            )
            if not claimed_state:
                raise ValueError(f"Failed to claim sync state: sync_state_id={sync_state_id}")
            cursor_payload = cursor_payload if cursor_payload is not None else claimed_state.cursor_payload
            last_seen_video_url = (
                last_seen_video_url if last_seen_video_url is not None else claimed_state.last_seen_video_url
            )

        request = SubscriptionUpdateRequest(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=payload.get("user_id"),
            force=bool(payload.get("force", False)),
            trace_id=trace_id,
            request_id=request_id,
            run_id=run_id,
            sync_state_id=sync_state_id,
            queue_token=queue_token,
            cursor_payload=cursor_payload,
            last_seen_video_url=last_seen_video_url,
            inline_video_extraction=bool(payload.get("inline_video_extraction", False)),
        )
        return self._orchestrator.update(request)

    def execute_subscription_sync_task(self, task: CrawlTask):
        return self.execute_subscription_sync_payload(task.payload or {})

    def _resolve_subscription_url(self, subscription_id: int) -> str:
        subscription = self._subscription_service.get_subscription_by_id(subscription_id)
        if not subscription or not subscription.url:
            raise ValueError(f"Subscription URL not found: {subscription_id}")
        return subscription.url

    @staticmethod
    def _parse_mode(raw: str | None) -> UpdateMode:
        if str(raw).lower() == UpdateMode.FULL.value:
            return UpdateMode.FULL
        if str(raw).lower() == UpdateMode.INCREMENTAL.value:
            return UpdateMode.INCREMENTAL
        return UpdateMode.SMART


subscription_sync_executor = CrawlExecutorService()
execute_subscription_sync_payload = subscription_sync_executor.execute_subscription_sync_payload
execute_subscription_sync_task = subscription_sync_executor.execute_subscription_sync_task
