import logging
import threading

from sqlalchemy.orm import Session

from core.cache import RedisClient
from core.database import get_session
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

    def run(self):
        while self.running:
            try:
                message = self._dequeue_message()
                if message:
                    with get_session() as session:
                        # 重新附加消息到新的会话
                        session.add(message)
                        self._process_message(message, session)
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)

    def _dequeue_message(self):
        with get_session() as session:
            message = self.mq.wait_and_dequeue(session=session, timeout=5)
            if message:
                self._handle_message(message, session)
                session.expunge(message)
        return message

    def _handle_message(self, message, session: Session):
        try:
            message.send_status = 'SUCCESS'
            session.commit()
        except Exception as e:
            logger.error(f"处理消息状态时发生错误: {e}", exc_info=True)

    def _process_message(self, message, session):
        raise NotImplementedError("Subclasses must implement this method")

    def stop(self):
        self.running = False

    def get_queue_thread_name(self):
        return f"{self.queue_name}-{self.id}"
