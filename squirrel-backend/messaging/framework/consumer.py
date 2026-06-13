from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Event
from typing import Any, Literal, Protocol

from core.cache import redis_client as default_redis_client

from .message import MqMessage

logger = logging.getLogger(__name__)


class QueueHandler(Protocol):
    def __call__(self, message: dict[str, Any]) -> None:
        ...


@dataclass
class ConsumerOptions:
    group: str
    consumer_name: str
    block_ms: int = 1000
    read_count: int = 1
    auto_ack: bool = True
    retry_dlq: str | None = None
    max_delivery: int = 16
    failure_action: Literal["retry", "dlq", "ack_delete"] = "dlq"

    def __post_init__(self) -> None:
        if self.failure_action == "dlq" and not self.retry_dlq:
            raise ValueError("retry_dlq is required when failure_action is dlq")
        if self.max_delivery < 1:
            raise ValueError("max_delivery must be >= 1")


class RedisStreamConsumer:
    """Redis Streams consumer with explicit retry and dead-letter behavior."""

    def __init__(self, stream: str, handler: QueueHandler, options: ConsumerOptions, redis_client=None):
        self.stream = stream
        self.handler = handler
        self.options = options
        self._redis = redis_client or default_redis_client
        self._error_sleep_sec = 0.01

        self._ensure_group()

    def _ensure_group(self) -> None:
        try:
            self._redis.xgroup_create(name=self.stream, groupname=self.options.group, id="0", mkstream=True)
            logger.info(
                "Created Redis Stream consumer group stream=%s group=%s",
                self.stream,
                self.options.group,
            )
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug(
                    "Redis Stream consumer group already exists stream=%s group=%s",
                    self.stream,
                    self.options.group,
                )
                return
            logger.exception(
                "Failed to create Redis Stream consumer group stream=%s group=%s",
                self.stream,
                self.options.group,
            )
            raise

    @staticmethod
    def _parse_pending_deliveries(entry: Any) -> int:
        if entry is None:
            return 0
        if isinstance(entry, dict):
            return int(entry.get("times_delivered") or entry.get("delivery_count") or 0)
        if isinstance(entry, (list, tuple)) and len(entry) >= 4:
            return int(entry[3] or 0)
        return int(getattr(entry, "times_delivered", None) or getattr(entry, "delivery_count", None) or 0)

    def _get_pending_deliveries(self, message_id: str) -> int:
        info = self._redis.xpending_range(
            self.stream,
            self.options.group,
            min=message_id,
            max=message_id,
            count=1,
        )
        if not info:
            return 0
        return self._parse_pending_deliveries(info[0])

    def _ack_delete(self, message_id: str) -> None:
        acked = self._redis.xack(self.stream, self.options.group, message_id)
        if acked:
            self._redis.xdel(self.stream, message_id)

    def _handle_failed_message(self, message_id: str, body: dict[str, Any]) -> None:
        if self.options.failure_action == "retry":
            logger.warning(
                "Message left pending for retry stream=%s message_id=%s",
                self.stream,
                message_id,
            )
            return
        if self.options.failure_action == "ack_delete":
            self._ack_delete(message_id)
            logger.warning(
                "Failed message acknowledged and deleted stream=%s message_id=%s",
                self.stream,
                message_id,
            )
            return

        try:
            deliveries = self._get_pending_deliveries(message_id)
            if deliveries >= self.options.max_delivery:
                from utils.trace import get_trace_id
                self._redis.xadd(self.options.retry_dlq, MqMessage(body={"body": body, "message_id": message_id}, trace_id=get_trace_id()).to_stream_fields())
                self._ack_delete(message_id)
                logger.warning(
                    "Message sent to DLQ stream=%s message_id=%s delivery_count=%s dlq=%s",
                    self.stream,
                    message_id,
                    deliveries,
                    self.options.retry_dlq,
                )
                return
            logger.warning(
                "Message left pending until max delivery stream=%s message_id=%s delivery_count=%s max_delivery=%s",
                self.stream,
                message_id,
                deliveries,
                self.options.max_delivery,
            )
        except Exception:
            logger.exception(
                "Failed to handle failed message stream=%s message_id=%s",
                self.stream,
                message_id,
            )

    def poll_once(self) -> bool:
        try:
            results = self._redis.xreadgroup(
                groupname=self.options.group,
                consumername=self.options.consumer_name,
                streams={self.stream: "0"},
                count=self.options.read_count,
                block=0,
            )

            if not results or not results[0][1]:
                results = self._redis.xreadgroup(
                    groupname=self.options.group,
                    consumername=self.options.consumer_name,
                    streams={self.stream: ">"},
                    count=self.options.read_count,
                    block=self.options.block_ms,
                )

            if not results:
                self._error_sleep_sec = 0.01
                return False
            for _, messages in results:
                logger.debug(
                    "Read %d messages from stream=%s",
                    len(messages),
                    self.stream,
                )
                for message_id, fields in messages:
                    msg = MqMessage.from_stream_fields(fields)
                    try:
                        from utils.trace import set_trace_id
                        set_trace_id(msg.trace_id)

                        logger.debug(
                            "Handling message stream=%s message_id=%s",
                            self.stream,
                            message_id,
                        )
                        self.handler(msg.body)
                    except Exception:
                        logger.exception(
                            "Message handler failed stream=%s message_id=%s",
                            self.stream,
                            message_id,
                        )
                        self._handle_failed_message(message_id, msg.body)
                        continue

                    if self.options.auto_ack:
                        try:
                            self._ack_delete(message_id)
                            logger.debug(
                                "Message acknowledged and deleted stream=%s message_id=%s",
                                self.stream,
                                message_id,
                            )
                        except Exception:
                            logger.warning(
                                "Failed to acknowledge or delete message stream=%s message_id=%s",
                                self.stream,
                                message_id,
                                exc_info=True,
                            )
            self._error_sleep_sec = 0.01
            return True
        except Exception as e:
            if "NOGROUP" in str(e):
                logger.warning(
                    "Consumer group is missing, recreating stream=%s group=%s",
                    self.stream,
                    self.options.group,
                )
                try:
                    self._ensure_group()
                except Exception:
                    logger.exception(
                        "Failed to recreate consumer group stream=%s group=%s",
                        self.stream,
                        self.options.group,
                    )
            else:
                logger.exception(
                    "Failed to poll messages stream=%s group=%s consumer=%s",
                    self.stream,
                    self.options.group,
                    self.options.consumer_name,
                )
            sleep_sec = self._error_sleep_sec
            self._error_sleep_sec = min(self._error_sleep_sec * 2, 5)
            time.sleep(sleep_sec)
            return False

    def start_loop(self, stop_event: Event | None = None) -> None:
        while stop_event is None or not stop_event.is_set():
            self.poll_once()
