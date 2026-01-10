from __future__ import annotations

import inspect
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.cache import redis_client as default_redis_client
from .message import MqMessage


logger = logging.getLogger()


@dataclass
class ConsumerOptions:
    group: str
    consumer_name: str
    block_ms: int = 1000
    read_count: int = 1
    auto_ack: bool = True
    retry_dlq: Optional[str] = None
    max_delivery: int = 16


class RedisStreamConsumer:
    """基于 Redis Streams 的消费者

    使用消费者组进行消费，具备基本的重试与死信支持。
    """

    def __init__(self, stream: str, handler: Callable[[Dict[str, Any]], None], options: ConsumerOptions, redis_client=None):
        self.stream = stream
        self.handler = handler
        self.options = options
        self._redis = redis_client or default_redis_client
        self._error_sleep_sec = 0.01
        # 如果处理函数签名为 (message, stream)，则在回调时同时传入 stream
        try:
            sig = inspect.signature(handler)
            self._pass_stream = len(sig.parameters) >= 2
        except Exception:
            self._pass_stream = False

        self._ensure_group()

    def _ensure_group(self) -> None:
        try:
            # MKSTREAM 确保创建 stream
            # 使用 id=0 确保能消费创建消费者组之前已经存在的 backlog 消息
            self._redis.xgroup_create(name=self.stream, groupname=self.options.group, id="0", mkstream=True)
            logger.info(
                "已创建 Redis Stream 消费者组 stream=%s group=%s",
                self.stream,
                self.options.group,
            )
        except Exception as e:
            # BUSYGROUP 表示已存在
            if "BUSYGROUP" in str(e):
                logger.debug(
                    "Redis Stream 消费者组已存在 stream=%s group=%s",
                    self.stream,
                    self.options.group,
                )
                return
            # 其他错误抛出
            logger.exception(
                "创建 Redis Stream 消费者组失败 stream=%s group=%s",
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

    def _nack_or_dlq(self, message_id: str, body: Dict[str, Any]) -> None:      
        if not self.options.retry_dlq:
            return
        try:
            # 读取 pending 次数
            deliveries = self._get_pending_deliveries(message_id)
            if deliveries >= self.options.max_delivery:
                # 推送到 DLQ，保留原消息的 trace_id
                from utils.trace import get_trace_id
                self._redis.xadd(self.options.retry_dlq, MqMessage(body={"body": body, "message_id": message_id}, trace_id=get_trace_id()).to_stream_fields())
                # ACK 原消息
                acked = self._redis.xack(self.stream, self.options.group, message_id)
                if acked:
                    self._redis.xdel(self.stream, message_id)
                logger.warning(
                    "消息已发送至 DLQ stream=%s message_id=%s delivery_count=%s dlq=%s",
                    self.stream,
                    message_id,
                    deliveries,
                    self.options.retry_dlq,
                )
        except Exception:
            logger.exception(
                "处理 DLQ 逻辑异常 stream=%s message_id=%s",
                self.stream,
                message_id,
            )

    def poll_once(self) -> bool:
        try:
            # 先尝试读取 pending 消息（之前读取但未确认的消息）
            results = self._redis.xreadgroup(
                groupname=self.options.group,
                consumername=self.options.consumer_name,
                streams={self.stream: "0"},
                count=self.options.read_count,
                block=0,  # 不阻塞，立即返回
            )
            
            # 如果没有 pending 消息，读取新消息
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
            # results: List[ (stream, [ (id, fields), ... ]) ]
            for _, messages in results:
                logger.debug(
                    "从 stream=%s 读取到 %d 条消息",
                    self.stream,
                    len(messages),
                )
                for message_id, fields in messages:
                    msg = MqMessage.from_stream_fields(fields)
                    try:
                        # 设置消息的 trace_id 到当前上下文，实现链路追踪        
                        from utils.trace import set_trace_id
                        set_trace_id(msg.trace_id)
                        
                        logger.debug(
                            "开始处理消息 stream=%s message_id=%s",
                            self.stream,
                            message_id,
                        )
                        if self._pass_stream:
                            self.handler(msg.body, self.stream)
                        else:
                            self.handler(msg.body)
                    except Exception:
                        logger.exception(
                            "处理消息失败 stream=%s message_id=%s",
                            self.stream,
                            message_id,
                        )
                        # 失败时尝试 DLQ
                        self._nack_or_dlq(message_id, msg.body)
                        continue

                    if self.options.auto_ack:
                        acked = self._redis.xack(self.stream, self.options.group, message_id)
                        if acked:
                            try:
                                self._redis.xdel(self.stream, message_id)
                                logger.debug(
                                    "消息已 ACK 并删除 stream=%s message_id=%s",
                                    self.stream,
                                    message_id,
                                )
                            except Exception:
                                logger.warning(
                                    "消息已 ACK 但删除失败 stream=%s message_id=%s",
                                    self.stream,
                                    message_id,
                                    exc_info=True,
                                )
            self._error_sleep_sec = 0.01
            return True
        except Exception as e:
            if "NOGROUP" in str(e):
                logger.warning(
                    "消费者组不存在，尝试重建 stream=%s group=%s",
                    self.stream,
                    self.options.group,
                )
                try:
                    self._ensure_group()
                except Exception:
                    logger.exception(
                        "重建消费者组失败 stream=%s group=%s",
                        self.stream,
                        self.options.group,
                    )
            else:
                logger.exception(
                    "轮询消息失败 stream=%s group=%s consumer=%s",
                    self.stream,
                    self.options.group,
                    self.options.consumer_name,
                )
            sleep_sec = self._error_sleep_sec
            self._error_sleep_sec = min(self._error_sleep_sec * 2, 5)
            time.sleep(sleep_sec)
            return False

    def start_loop(self) -> None:
        while True:
            self.poll_once()


