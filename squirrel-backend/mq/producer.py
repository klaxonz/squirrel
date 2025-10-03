from __future__ import annotations

import logging
import time
from typing import Optional, Dict

from core.cache import redis_client
from .message import MqMessage

logger = logging.getLogger()


class RedisStreamProducer:
    """基于 Redis Streams 的生产者

    使用 XADD 追加消息，消息字段遵循 `MqMessage` 约定。
    支持简单的重试与退避。
    支持链路追踪：自动从当前上下文获取 trace_id 并传递到消息中。
    """

    def __init__(self):
        ...

    def send(self, stream: str, message: Dict, max_retries: int = 3, approximate_maxlen: Optional[int] = 100000, trace_id: Optional[str] = None) -> str:
        # 如果未指定 trace_id，则从当前上下文获取
        if trace_id is None:
            from utils.trace import get_trace_id
            trace_id = get_trace_id()
        
        # 记录消息追踪
        try:
            from services import message_service
            message_type = message.get('type') or message.get('action')
            message_service.record_message_trace(
                trace_id=trace_id,
                queue_name=stream,
                message_type=message_type,
                body=message,
                status='PENDING'
            )
            logger.debug(f"记录消息追踪 trace_id={trace_id} queue={stream} type={message_type}")
        except Exception as e:
            logger.warning(f"记录消息追踪失败: {e}")
        
        payload = MqMessage(body=message, trace_id=trace_id).to_stream_fields()
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                # 使用近似裁剪，避免无界增长
                msg_id = redis_client.xadd(stream, payload, maxlen=approximate_maxlen, approximate=True)
                return msg_id  # type: ignore[return-value]
            except Exception as e:
                last_err = e
                if attempt < max_retries:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    # 记录发送失败
                    try:
                        from services import message_service
                        message_service.update_message_status(
                            trace_id=trace_id,
                            status='FAILED',
                            error_msg=f"发送失败: {str(e)}"
                        )
                    except:
                        pass
                    raise last_err


