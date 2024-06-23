import json
import uuid

from .cache import RedisClient


class RedisMessageQueue:
    def __init__(self, queue_name):
        """
        初始化Redis消息队列客户端
        :param queue_name: 消息队列的名称
        :param args: 传递给RedisClient的其他参数
        :param kwargs: 传递给RedisClient的其他关键字参数
        """
        self.client = RedisClient.get_instance().client
        self.queue_name = queue_name

    def enqueue(self, message_obj):
        """
        序列化消息体并将其添加到队列尾部
        :param message_obj: Message对象实例
        :return: 新队列长度
        """
        serialized_message = json.dumps(message_obj.__dict__)
        return self.client.rpush(self.queue_name, serialized_message)

    def dequeue(self, block=True, timeout=0):
        """
        从队列头部取出一条消息并反序列化为Message对象
        :param block: 是否阻塞等待
        :param timeout: 阻塞等待的超时时间（秒）
        :return: Message对象实例，如果队列为空且非阻塞模式，则返回None
        """
        raw_message = self.client.dequeue(block=block, timeout=timeout)
        if raw_message:
            return Message(**json.loads(raw_message))
        return None

    def wait_and_dequeue(self, timeout=None):
        """
        阻塞等待并从队列头部取出一条消息
        :param timeout: 等待超时时间（秒），None表示无限等待
        :return: Message对象实例，如果超时则返回None
        """
        raw_message = self.client.blpop(self.queue_name, timeout=timeout)
        if raw_message:
            return Message.from_dict(json.loads(raw_message[1]))
        return None

    def queue_length(self):
        """
        获取当前队列长度
        :return: 队列长度
        """
        return self.client.llen(self.queue_name)

    def clear_queue(self):
        """
        清空队列
        :return: 被移除的元素数量
        """
        return self.client.ltrim(self.queue_name, -1, 0)  # 保留队列中的第一个元素（实际上等于清空）


class Message:
    def __init__(self, content, message_id=None, type=None):
        """
        初始化消息体
        :param content: 消息内容
        :param message_id: 消息ID，如果不提供则自动生成
        """
        self.message_id = message_id or str(uuid.uuid4()).replace('-', '')
        self.content = content
        self.type = type

    @classmethod
    def from_dict(cls, data_dict):
        """
        从字典创建Message实例，用于反序列化
        :param data_dict: 包含消息ID和内容的字典
        :return: Message实例
        """
        return cls(content=data_dict['content'], message_id=data_dict['message_id'], type=data_dict['type'])

