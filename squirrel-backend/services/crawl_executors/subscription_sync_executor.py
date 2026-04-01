from __future__ import annotations

from models.crawl_task import CrawlTask
from services import subscription_service, subscription_sync_state_service
from services.subscription_update.models import SubscriptionUpdateRequest, UpdateMode, UpdateTrigger
from services.subscription_update.orchestrator import orchestrator


def execute_subscription_sync_payload(payload: dict):
    subscription_id = int(payload['subscription_id'])
    url = payload.get('url') or _resolve_subscription_url(subscription_id)
    trigger = _parse_trigger(payload.get('trigger'))
    mode = _parse_mode(payload.get('mode'))
    sync_state_id = payload.get('sync_state_id')
    queue_token = payload.get('queue_token')
    request_id = payload.get('request_id')
    run_id = payload.get('run_id')
    trace_id = payload.get('trace_id')
    cursor_payload = payload.get('cursor_payload')
    last_seen_video_url = payload.get('last_seen_video_url')

    if sync_state_id and queue_token:
        claimed_state = subscription_sync_state_service.claim_sync_state(
            int(sync_state_id),
            queue_token,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger.value,
        )
        if not claimed_state:
            raise ValueError(f'Failed to claim sync state: sync_state_id={sync_state_id}')
        cursor_payload = cursor_payload if cursor_payload is not None else claimed_state.cursor_payload
        last_seen_video_url = (
            last_seen_video_url if last_seen_video_url is not None else claimed_state.last_seen_video_url
        )

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
        cursor_payload=cursor_payload,
        last_seen_video_url=last_seen_video_url,
    )
    return orchestrator.update(request)


def execute_subscription_sync_task(task: CrawlTask):
    return execute_subscription_sync_payload(task.payload or {})


def _resolve_subscription_url(subscription_id: int) -> str:
    subscription = subscription_service.get_subscription_by_id(subscription_id)
    if not subscription or not subscription.url:
        raise ValueError(f'Subscription URL not found: {subscription_id}')
    return subscription.url


def _parse_trigger(raw: str | None) -> UpdateTrigger:
    if str(raw).lower() == UpdateTrigger.MANUAL.value:
        return UpdateTrigger.MANUAL
    if str(raw).lower() == UpdateTrigger.API.value:
        return UpdateTrigger.API
    return UpdateTrigger.SCHEDULED


def _parse_mode(raw: str | None) -> UpdateMode:
    if str(raw).lower() == UpdateMode.FULL.value:
        return UpdateMode.FULL
    if str(raw).lower() == UpdateMode.INCREMENTAL.value:
        return UpdateMode.INCREMENTAL
    return UpdateMode.SMART
