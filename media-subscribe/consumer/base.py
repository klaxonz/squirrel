import logging
import threading

from sqlalchemy.orm import Session

from common.cache import RedisClient
from common.message_queue import RedisMessageQueue

logger = logging.getLogger(__name__)


class BaseConsumerThread(threading.Thread):
    """Base class for consumer threads to handle common setup and teardown."""

    def __init__(self, queue_name, thread_id):
        super().__init__()
        self.queue_name = queue_name
        self.id = thread_id
        self.running = True
        self.redis = RedisClient.get_instance().client  # Cache Redis client instance
        self.mq = RedisMessageQueue(queue_name=self.queue_name)  # Initialize MQ once

    def handle_message(self, message, session: Session):
        """Handle a generic message pattern to reduce duplication."""
        try:
            message.send_status = 'SUCCESS'
            session.commit()
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}", exc_info=True)

    def stop(self):
        self.running = False

    def get_queue_thread_name(self):
        return f"{self.queue_name}-{self.id}"
