from __future__ import annotations

import logging
import time

from infrastructure.cache.redis_client import redis_client

from .message import MqMessage

logger = logging.getLogger(__name__)


class RedisStreamProducer:
    """Producer based on Redis Streams

    Appends messages using XADD, fields follow the `MqMessage` convention.
    Supports simple retry and backoff.
    Supports trace tracking: automatically extracts trace_id from current context and passes it to the message.
    """

    def __init__(self):
        ...

    @staticmethod
    def _resolve_message_trace_id(message: dict) -> str | None:
        trace_id = message.get("trace_id")
        if trace_id in (None, ""):
            return None
        return str(trace_id)

    def send(self, stream: str, message: dict, max_retries: int = 3, approximate_maxlen: int | None = 100000, trace_id: str | None = None) -> str:
        if trace_id is None:
            trace_id = self._resolve_message_trace_id(message)
        if trace_id is None:
            from shared_kernel.infrastructure.trace import get_trace_id
            trace_id = get_trace_id()

        payload = MqMessage(body=message, trace_id=trace_id).to_stream_fields()

        for attempt in range(max_retries + 1):
            try:
                # Use approximate trimming to prevent unbounded growth
                msg_id = redis_client.xadd(stream, payload, maxlen=approximate_maxlen, approximate=True)
                return msg_id  # type: ignore[return-value]
            except (ConnectionError, OSError, ValueError, TypeError) as e:
                last_err = e
                if attempt < max_retries:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    logger.error(
                        "Failed to send message stream=%s after %s retries: %s",
                        stream,
                        max_retries,
                        e,
                    )
                    raise last_err
