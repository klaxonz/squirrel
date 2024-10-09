import json
import logging
import time
from typing import Optional

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from model.message import Message, MessageSchema
from core.cache import RedisClient


class RedisMessageQueue:
    def __init__(self, queue_name: str):
        """
        初始化Redis消息队列客户端
        :param queue_name: 消息队列的名称
        """
        self.client: Redis = RedisClient.get_instance().get_client()
        self.queue_name = queue_name

    def enqueue(self, message: Message, retry_attempts: int = 3, retry_delay: float = 1) -> Optional[int]:
        """
        序列化消息体并将其添加到队列尾部
        :param message: Message对象实例
        :param retry_attempts: 重试次数
        :param retry_delay: 重试间隔（秒）
        :return: 新队列长度，如果出错则返回None
        """
        for attempt in range(retry_attempts):
            try:
                return self.client.rpush(self.queue_name, MessageSchema().dumps(message))
            except RedisError as e:
                if attempt == retry_attempts - 1:
                    logging.error(f"Failed to enqueue message after {retry_attempts} attempts: {str(e)}")
                    return None
                time.sleep(retry_delay)

    def enqueue_head(self, message: Message) -> Optional[int]:
        """
        序列化消息体并将其添加到队列头部
        :param message: Message对象实例
        :return: 新队列长度，如果出错则返回None
        """
        try:
            return self.client.lpush(self.queue_name, MessageSchema().dumps(message))
        except RedisError as e:
            logging.error(f"Error enqueueing message to head: {str(e)}")
            return None

    def dequeue(self, block: bool = True, timeout: int = 0) -> Optional[Message]:
        """
        从队列头部取出一条消息并反序列化为Message对象
        :param block: 是否阻塞等待
        :param timeout: 阻塞等待的超时时间（秒）
        :return: Message对象实例，如果队列为空且非阻塞模式，则返回None
        """
        try:
            if block:
                raw_message = self.client.blpop([self.queue_name], timeout=timeout)
                if raw_message:
                    return MessageSchema().loads(raw_message[1])
            else:
                raw_message = self.client.lpop(self.queue_name)
                if raw_message:
                    return MessageSchema().loads(raw_message)
        except RedisError as e:
            # 记录错误日志
            logging.error(f"Error dequeue message: {str(e)}")
        return None

    def wait_and_dequeue(self, session: Session, timeout: Optional[int] = None) -> Optional[Message]:
        """
        阻塞等待并从队列头部取出一条消息
        :param session:
        :param timeout: 等待超时时间（秒），None表示无限等待
        :return: Message对象实例，如果超时或出错则返回None
        """
        try:
            raw_message = self.client.blpop([self.queue_name], timeout=timeout)
            if raw_message:
                return MessageSchema().load(json.loads(raw_message[1]), session=session)
        except (RedisError, json.JSONDecodeError) as e:
            logging.error(f"Error in wait_and_dequeue: {str(e)}")
        return None

    def queue_length(self) -> int:
        """
        获取当前队列长度
        :return: 队列长度
        """
        try:
            return self.client.llen(self.queue_name)
        except RedisError as e:
            logging.error(f"Error getting queue length: {str(e)}")
            return 0

    def clear_queue(self) -> int:
        """
        清空队列
        :return: 被移除的元素数量
        """
        try:
            length = self.queue_length()
            self.client.delete(self.queue_name)
            return length
        except RedisError as e:
            logging.error(f"Error clearing queue: {str(e)}")
            return 0

    def acknowledge(self, message: Message) -> None:
        try:
            processed_queue = f"{self.queue_name}:processed"
            self.client.rpush(processed_queue, MessageSchema().dumps(message))
        except RedisError as e:
            logging.error(f"Error acknowledging message: {str(e)}")

    def requeue_unacknowledged(self, timeout: int = 3600) -> None:
        try:
            processed_queue = f"{self.queue_name}:processed"
            while True:
                raw_message = self.client.brpoplpush(processed_queue, self.queue_name, timeout)
                if not raw_message:
                    break
        except RedisError as e:
            logging.error(f"Error requeuing unacknowledged messages: {str(e)}")

    def get_queue_stats(self) -> dict:
        try:
            return {
                "queue_length": self.client.llen(self.queue_name),
                "processed_length": self.client.llen(f"{self.queue_name}:processed"),
            }
        except RedisError as e:
            logging.error(f"Error getting queue stats: {str(e)}")
            return {}
