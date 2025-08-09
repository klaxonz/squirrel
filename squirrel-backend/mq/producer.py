from __future__ import annotations

import time
from typing import Optional, Dict

from core.cache import RedisClient
from .message import MqMessage


class RedisStreamProducer:
    """基于 Redis Streams 的生产者

    使用 XADD 追加消息，消息字段遵循 `MqMessage` 约定。
    支持简单的重试与退避。
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client or RedisClient.get_instance().get_client()

    def send(self, stream: str, message: Dict, max_retries: int = 3, approximate_maxlen: Optional[int] = 100000) -> str:
        payload = MqMessage(body=message).to_stream_fields()
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                # 使用近似裁剪，避免无界增长
                msg_id = self._redis.xadd(stream, payload, maxlen=approximate_maxlen, approximate=True)
                return msg_id  # type: ignore[return-value]
            except Exception as e:
                last_err = e
                if attempt < max_retries:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise last_err


