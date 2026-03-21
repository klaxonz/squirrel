from __future__ import annotations

import logging
import time
from typing import Optional, Dict

from core.cache import redis_client
from .message import MqMessage
from utils.metrics import metrics

logger = logging.getLogger()


class RedisStreamProducer:
    """基于 Redis Streams 的生产者

    使用 XADD 追加消息，消息字段遵循 `MqMessage` 约定。
    支持简单的重试与退避。
    支持链路追踪：自动从当前上下文获取 trace_id 并传递到消息中。
    """

    def __init__(self):
        ...

    @staticmethod
    def _resolve_message_trace_id(message: Dict) -> Optional[str]:
        trace_id = message.get('trace_id')
        if trace_id in (None, ''):
            return None
        return str(trace_id)

    def send(self, stream: str, message: Dict, max_retries: int = 3, approximate_maxlen: Optional[int] = 100000, trace_id: Optional[str] = None) -> str:
        if trace_id is None:
            trace_id = self._resolve_message_trace_id(message)
        if trace_id is None:
            from utils.trace import get_trace_id
            trace_id = get_trace_id()

        payload = MqMessage(body=message, trace_id=trace_id).to_stream_fields()
        tags = {"queue": stream}
        
        for attempt in range(max_retries + 1):
            try:
                # 使用近似裁剪，避免无界增长
                msg_id = redis_client.xadd(stream, payload, maxlen=approximate_maxlen, approximate=True)
                
                # 记录消息发送成功
                metrics.counter("queue.messages.total", tags={**tags, "action": "publish", "status": "success"})
                
                # 更新队列深度
                try:
                    depth = redis_client.xlen(stream)
                    metrics.gauge("queue.depth", depth, tags=tags)
                except Exception:
                    pass  # 队列深度查询失败不影响主流程
                
                return msg_id  # type: ignore[return-value]
            except Exception as e:
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
                    metrics.counter("queue.messages.total", tags={**tags, "action": "publish", "status": "error"})
                    raise last_err


