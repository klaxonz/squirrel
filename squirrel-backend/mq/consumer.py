from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List
import inspect

from core.cache import RedisClient
from .message import MqMessage


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
        self._redis = redis_client or RedisClient.get_instance().get_client()
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
            self._redis.xgroup_create(name=self.stream, groupname=self.options.group, id="$", mkstream=True)
        except Exception as e:
            # BUSYGROUP 表示已存在
            if "BUSYGROUP" in str(e):
                return
            # 其他错误抛出
            raise

    def _nack_or_dlq(self, message_id: str, body: Dict[str, Any]) -> None:
        if not self.options.retry_dlq:
            return
        try:
            # 读取 pending 次数
            info = self._redis.xpending_range(self.stream, self.options.group, min="-", max="+", count=1, consumername=self.options.consumer_name)
            deliveries = 0
            for entry in info:
                if getattr(entry, "message_id", None) == message_id:
                    deliveries = getattr(entry, "delivery_count", 0)
                    break
            if deliveries >= self.options.max_delivery:
                # 推送到 DLQ
                self._redis.xadd(self.options.retry_dlq, MqMessage(body={"body": body, "message_id": message_id}).to_stream_fields())
                # ACK 原消息
                self._redis.xack(self.stream, self.options.group, message_id)
        except Exception:
            pass

    def poll_once(self) -> bool:
        try:
            results = self._redis.xreadgroup(
                groupname=self.options.group,
                consumername=self.options.consumer_name,
                streams={self.stream: ">"},
                count=self.options.read_count,
                block=self.options.block_ms,
            )
            if not results:
                return False
            # results: List[ (stream, [ (id, fields), ... ]) ]
            for _, messages in results:
                for message_id, fields in messages:
                    msg = MqMessage.from_stream_fields(fields)
                    try:
                        if self._pass_stream:
                            self.handler(msg.body, self.stream)
                        else:
                            self.handler(msg.body)
                        if self.options.auto_ack:
                            self._redis.xack(self.stream, self.options.group, message_id)
                    except Exception:
                        # 失败时尝试 DLQ
                        self._nack_or_dlq(message_id, msg.body)
            return True
        except Exception:
            time.sleep(0.2)
            return False

    def start_loop(self) -> None:
        while True:
            self.poll_once()
            time.sleep(0.05)


