import asyncio
import json
import logging
from datetime import datetime
from time import monotonic
from typing import Any

from core.cache import create_redis_client
from services.subscription.sync.dashboard_service import subscription_sync_dashboard_service
from services.subscription.sync.history_service import subscription_sync_history_service
from services.sync_dashboard.channels import (
    SYNC_DASHBOARD_EXTRACT_CHANNEL,
    SYNC_DASHBOARD_FEED_CHANNEL,
    SYNC_DASHBOARD_HEARTBEAT_INTERVAL_SECONDS,
    SYNC_DASHBOARD_PUBSUB_TIMEOUT_SECONDS,
    SYNC_DASHBOARD_RUN_CHANNEL,
)
from services.video.extraction_center.service import video_extraction_center_service

logger = logging.getLogger(__name__)


class SyncDashboardStreamService:
    def __init__(self, session_factory=None, sync_dashboard_service=None, history_service=None, extraction_center_service=None):
        from core.database import get_session
        self.session_factory = session_factory or get_session
        self.sync_dashboard_service = sync_dashboard_service or subscription_sync_dashboard_service
        self.history_service = history_service or subscription_sync_history_service
        self.extraction_center_service = extraction_center_service or video_extraction_center_service

    @staticmethod
    def _json_default(value: Any):
        if hasattr(value, 'model_dump'):
            return value.model_dump(mode='json')
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')

    @staticmethod
    def encode_sse_event(event_name: str, payload: dict) -> str:
        return f'event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False, default=SyncDashboardStreamService._json_default)}\n\n'

    @staticmethod
    def publish_sync_dashboard_invalidation(channel: str, payload: dict | None = None) -> None:
        client = create_redis_client()
        serialized_payload = json.dumps(payload or {}, ensure_ascii=False)
        client.publish(channel, serialized_payload)

    def _load_feed_snapshot(self, user_id: int) -> dict:
        return self.sync_dashboard_service.get_feed_dashboard_snapshot(
            user_id=user_id,
            site=None,
            query=None,
            date_from=None,
            date_to=None,
        )

    def _load_extract_snapshot(self, user_id: int) -> dict:
        return self.extraction_center_service.get_extraction_dashboard_snapshot(user_id)

    def _load_run_detail_snapshot(self, user_id: int, selected_run_id: str | None) -> dict | None:
        if not selected_run_id:
            return None
        return self.history_service.get_run_detail_snapshot(selected_run_id, user_id) or {
            'run': None,
            'events': [],
        }

    @staticmethod
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

    async def stream_sync_dashboard_events(
        self,
        *,
        user_id: int,
        selected_run_id: str | None,
        redis_client=None,
        heartbeat_interval: int = SYNC_DASHBOARD_HEARTBEAT_INTERVAL_SECONDS,
    ):
        stream_started_at = monotonic()
        logger.info(
            'Opening sync dashboard SSE stream user_id=%s selected_run_id=%s',
            user_id,
            selected_run_id or '',
        )

        feed_snapshot = self._load_feed_snapshot(user_id)
        logger.info(
            'Loaded sync dashboard SSE feed snapshot user_id=%s selected_run_id=%s elapsed_ms=%s',
            user_id,
            selected_run_id or '',
            int((monotonic() - stream_started_at) * 1000),
        )
        yield self.encode_sse_event('feed_snapshot', feed_snapshot)

        extract_snapshot = self._load_extract_snapshot(user_id)
        logger.info(
            'Loaded sync dashboard SSE extract snapshot user_id=%s selected_run_id=%s elapsed_ms=%s',
            user_id,
            selected_run_id or '',
            int((monotonic() - stream_started_at) * 1000),
        )
        yield self.encode_sse_event('extract_snapshot', extract_snapshot)

        run_detail_snapshot = self._load_run_detail_snapshot(user_id, selected_run_id)
        if run_detail_snapshot is not None:
            yield self.encode_sse_event('run_detail', run_detail_snapshot)

        logger.info(
            'Loaded sync dashboard SSE initial snapshots user_id=%s selected_run_id=%s elapsed_ms=%s',
            user_id,
            selected_run_id or '',
            int((monotonic() - stream_started_at) * 1000),
        )

        client = redis_client or create_redis_client()
        pubsub = client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(
            SYNC_DASHBOARD_FEED_CHANNEL,
            SYNC_DASHBOARD_EXTRACT_CHANNEL,
            SYNC_DASHBOARD_RUN_CHANNEL,
        )
        last_heartbeat = monotonic()

        try:
            while True:
                message = await asyncio.to_thread(pubsub.get_message, timeout=SYNC_DASHBOARD_PUBSUB_TIMEOUT_SECONDS)
                if message and message.get('type') == 'message':
                    channel = message.get('channel')
                    payload = self._decode_message_payload(message.get('data'))

                    if channel == SYNC_DASHBOARD_FEED_CHANNEL:
                        yield self.encode_sse_event('feed_snapshot', self._load_feed_snapshot(user_id))
                    elif channel == SYNC_DASHBOARD_EXTRACT_CHANNEL:
                        yield self.encode_sse_event('extract_snapshot', self._load_extract_snapshot(user_id))
                    elif channel == SYNC_DASHBOARD_RUN_CHANNEL and selected_run_id:
                        if payload.get('run_id') == selected_run_id:
                            snapshot = self._load_run_detail_snapshot(user_id, selected_run_id)
                            if snapshot is not None:
                                yield self.encode_sse_event('run_detail', snapshot)

                if monotonic() - last_heartbeat >= heartbeat_interval:
                    yield self.encode_sse_event('heartbeat', {})
                    last_heartbeat = monotonic()

                await asyncio.sleep(0)
        finally:
            try:
                await asyncio.to_thread(pubsub.close)
            except Exception:  # cleanup — must not propagate
                logger.warning('Failed to close sync dashboard pubsub cleanly', exc_info=True)

sync_dashboard_stream_service = SyncDashboardStreamService()
