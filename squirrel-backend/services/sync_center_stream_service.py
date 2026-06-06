import asyncio
import json
import logging
from datetime import datetime
from time import monotonic
from typing import Any

from core.cache import create_redis_client
from services import (
    subscription_sync_center_service,
    subscription_sync_history_service,
    video_extraction_center_service,
)

logger = logging.getLogger(__name__)

SYNC_CENTER_FEED_CHANNEL = 'squirrel:sync-center:feed'
SYNC_CENTER_EXTRACT_CHANNEL = 'squirrel:sync-center:extract'
SYNC_CENTER_RUN_CHANNEL = 'squirrel:sync-center:run'
SYNC_CENTER_HEARTBEAT_INTERVAL_SECONDS = 15
SYNC_CENTER_PUBSUB_TIMEOUT_SECONDS = 1.0


def _json_default(value: Any):
    if hasattr(value, 'model_dump'):
        return value.model_dump(mode='json')
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')


def encode_sse_event(event_name: str, payload: dict) -> str:
    return f'event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False, default=_json_default)}\n\n'


def publish_sync_center_invalidation(channel: str, payload: dict | None = None) -> None:
    client = create_redis_client()
    serialized_payload = json.dumps(payload or {}, ensure_ascii=False)
    published_count = client.publish(channel, serialized_payload)


def _load_feed_snapshot(user_id: int) -> dict:
    return subscription_sync_center_service.get_feed_dashboard_snapshot(
        user_id=user_id,
        site=None,
        query=None,
        date_from=None,
        date_to=None,
    )


def _load_extract_snapshot(user_id: int) -> dict:
    return video_extraction_center_service.get_extraction_dashboard_snapshot(user_id)


def _load_run_detail_snapshot(user_id: int, selected_run_id: str | None) -> dict | None:
    if not selected_run_id:
        return None
    return subscription_sync_history_service.get_run_detail_snapshot(selected_run_id, user_id) or {
        'run': None,
        'events': [],
    }


def _decode_message_payload(data: Any) -> dict:
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    if isinstance(data, dict):
        return data
    return {}


async def stream_sync_center_events(
    *,
    user_id: int,
    selected_run_id: str | None,
    redis_client=None,
    heartbeat_interval: int = SYNC_CENTER_HEARTBEAT_INTERVAL_SECONDS,
):
    stream_started_at = monotonic()
    logger.info(
        'Opening sync-center SSE stream user_id=%s selected_run_id=%s',
        user_id,
        selected_run_id or '',
    )

    feed_snapshot = _load_feed_snapshot(user_id)
    logger.info(
        'Loaded sync-center SSE feed snapshot user_id=%s selected_run_id=%s elapsed_ms=%s',
        user_id,
        selected_run_id or '',
        int((monotonic() - stream_started_at) * 1000),
    )
    yield encode_sse_event('feed_snapshot', feed_snapshot)

    extract_snapshot = _load_extract_snapshot(user_id)
    logger.info(
        'Loaded sync-center SSE extract snapshot user_id=%s selected_run_id=%s elapsed_ms=%s',
        user_id,
        selected_run_id or '',
        int((monotonic() - stream_started_at) * 1000),
    )
    yield encode_sse_event('extract_snapshot', extract_snapshot)

    run_detail_snapshot = _load_run_detail_snapshot(user_id, selected_run_id)
    if run_detail_snapshot is not None:
        yield encode_sse_event('run_detail', run_detail_snapshot)

    logger.info(
        'Loaded sync-center SSE initial snapshots user_id=%s selected_run_id=%s elapsed_ms=%s',
        user_id,
        selected_run_id or '',
        int((monotonic() - stream_started_at) * 1000),
    )

    client = redis_client or create_redis_client()
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(
        SYNC_CENTER_FEED_CHANNEL,
        SYNC_CENTER_EXTRACT_CHANNEL,
        SYNC_CENTER_RUN_CHANNEL,
    )
    last_heartbeat = monotonic()

    try:
        while True:
            message = await asyncio.to_thread(pubsub.get_message, timeout=SYNC_CENTER_PUBSUB_TIMEOUT_SECONDS)
            if message and message.get('type') == 'message':
                channel = message.get('channel')
                payload = _decode_message_payload(message.get('data'))

                if channel == SYNC_CENTER_FEED_CHANNEL:
                    yield encode_sse_event('feed_snapshot', _load_feed_snapshot(user_id))
                elif channel == SYNC_CENTER_EXTRACT_CHANNEL:
                    yield encode_sse_event('extract_snapshot', _load_extract_snapshot(user_id))
                elif channel == SYNC_CENTER_RUN_CHANNEL and selected_run_id:
                    if payload.get('run_id') == selected_run_id:
                        snapshot = _load_run_detail_snapshot(user_id, selected_run_id)
                        if snapshot is not None:
                            yield encode_sse_event('run_detail', snapshot)

            if monotonic() - last_heartbeat >= heartbeat_interval:
                yield encode_sse_event('heartbeat', {})
                last_heartbeat = monotonic()

            await asyncio.sleep(0)
    finally:
        try:
            await asyncio.to_thread(pubsub.close)
        except Exception:  # cleanup — must not propagate
            logger.warning('Failed to close sync-center pubsub cleanly', exc_info=True)
