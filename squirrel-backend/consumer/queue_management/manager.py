import json
import logging
import time
from typing import Callable, Dict, Any, Optional, List, cast
from core.cache import RedisClient

logger = logging.getLogger(__name__)


class QueueManager:

    _stats = {
        "messages_sent": 0,
        "messages_processed": 0,
        "handlers_registered": 0,
        "send_errors": 0,
        "process_errors": 0
    }

    # 注册的处理器
    _handlers: Dict[str, Callable] = {}
    _pattern_handlers: List[tuple] = []  # (pattern, regex, handler)

    # Redis客户端
    _redis_client = None
    
    @classmethod
    def _get_redis_client(cls):
        """获取Redis客户端"""
        if cls._redis_client is None:
            cls._redis_client = RedisClient.get_instance().get_client()
        return cls._redis_client

    @classmethod
    def reset_redis_client(cls):
        """重置Redis客户端连接"""
        try:
            if cls._redis_client:
                cls._redis_client.connection_pool.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting Redis client: {e}")
        finally:
            cls._redis_client = None
            logger.info("Redis client reset")

    @classmethod
    def get_connection_pool_info(cls) -> dict:
        """获取连接池信息"""
        try:
            if cls._redis_client and hasattr(cls._redis_client, 'connection_pool'):
                pool = cls._redis_client.connection_pool
                return {
                    "max_connections": getattr(pool, 'max_connections', 'unknown'),
                    "created_connections": len(getattr(pool, '_created_connections', [])),
                    "available_connections": len(getattr(pool, '_available_connections', [])),
                    "in_use_connections": getattr(pool, 'max_connections', 0) - len(getattr(pool, '_available_connections', []))
                }
        except Exception as e:
            logger.warning(f"Error getting connection pool info: {e}")

        return {"status": "no_client_or_error"}

    @staticmethod
    def register_handler(queue_pattern: str, handler: Callable, **kwargs) -> None:
        """注册队列处理器

        支持精确队列名称和模式匹配。

        Args:
            queue_pattern: 队列名称或模式，支持通配符 *
            handler: 处理函数
            **kwargs: 额外参数（保留兼容性）

        """
        # kwargs用于保持向后兼容性，暂时不使用
        _ = kwargs
        try:
            # 验证参数
            if not queue_pattern or not isinstance(queue_pattern, str):
                raise ValueError("queue_pattern must be a non-empty string")

            if not callable(handler):
                raise ValueError("handler must be callable")

            if '*' in queue_pattern or '?' in queue_pattern:
                # 模式匹配队列
                import re
                regex_pattern = queue_pattern.replace('*', '.*').replace('?', '.')
                regex = re.compile(f'^{regex_pattern}$')
                QueueManager._pattern_handlers.append((queue_pattern, regex, handler))
                logger.info(f"Registered pattern handler: {queue_pattern}")
            else:
                # 精确队列名称
                QueueManager._handlers[queue_pattern] = handler
                logger.info(f"Registered exact handler: {queue_pattern}")

            QueueManager._stats["handlers_registered"] += 1

        except Exception as e:
            logger.error(f"Failed to register handler for {queue_pattern}: {e}")
            raise
    
    @staticmethod
    def send_message(queue_name: str, message: Any, max_retries: int = 3) -> None:
        """发送消息到指定队列

        Args:
            queue_name: 目标队列名称
            message: 要发送的消息
            max_retries: 最大重试次数
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # 验证队列名称
                if not queue_name or not isinstance(queue_name, str):
                    raise ValueError("queue_name must be a non-empty string")

                # 获取Redis客户端
                redis_client = QueueManager._get_redis_client()

                # 序列化消息
                message_json = json.dumps(message, ensure_ascii=False)

                # 发送消息到Redis队列（使用LPUSH）
                redis_client.lpush(queue_name, message_json)

                QueueManager._stats["messages_sent"] += 1
                logger.debug(f"Message sent to queue {queue_name}: {len(message_json)} bytes")
                return

            except Exception as e:
                last_error = e

                # 如果是连接池耗尽，尝试重置连接
                if "Too many connections" in str(e) and attempt == 0:
                    logger.warning(f"Redis connection pool exhausted, resetting client")
                    QueueManager.reset_redis_client()

                if attempt < max_retries:
                    wait_time = (attempt + 1) * 0.1  # 递增等待时间
                    logger.warning(f"Failed to send message to {queue_name} (attempt {attempt + 1}/{max_retries + 1}): {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    QueueManager._stats["send_errors"] += 1
                    logger.error(f"Failed to send message to {queue_name} after {max_retries + 1} attempts: {e}")
                    raise last_error

    @staticmethod
    def send_message_safe(queue_name: str, message: Any,
                         fallback_queue: Optional[str] = None) -> bool:
        """安全发送消息，失败时不抛出异常

        Args:
            queue_name: 目标队列名称
            message: 要发送的消息
            fallback_queue: 备用队列名称

        Returns:
            bool: 是否发送成功
        """
        try:
            QueueManager.send_message(queue_name, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {queue_name}: {e}")

            if fallback_queue:
                try:
                    QueueManager.send_message(fallback_queue, message)
                    logger.warning(f"Message sent to fallback queue {fallback_queue} "
                                 f"(original queue {queue_name} failed)")
                    return True
                except Exception as fallback_error:
                    logger.error(f"Fallback queue {fallback_queue} also failed: {fallback_error}")

            return False

    @staticmethod
    def get_handler(queue_name: str) -> Optional[Callable]:
        """获取队列对应的处理函数

        Args:
            queue_name: 队列名称

        Returns:
            Optional[Callable]: 处理函数，不存在时返回None
        """
        # 1. 查找精确匹配
        if queue_name in QueueManager._handlers:
            return QueueManager._handlers[queue_name]

        # 2. 查找模式匹配
        for pattern, regex, handler in QueueManager._pattern_handlers:
            if regex.match(queue_name):
                logger.debug(f"Pattern match found: {queue_name} matches {pattern}")
                return handler

        return None

    @staticmethod
    def process_message(queue_name: str, timeout: int = 10) -> bool:
        """从队列中处理一条消息

        Args:
            queue_name: 队列名称
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功处理了消息
        """
        try:
            # 获取Redis客户端
            redis_client = QueueManager._get_redis_client()

            # 从队列中拉取消息（阻塞式）
            result = redis_client.brpop([queue_name], timeout=timeout)

            if not result:
                # 超时，没有消息
                return False

            # brpop 返回 (queue_name, message) 元组
            result = cast(tuple[str, str], result)
            _, message_json = result

            # 反序列化消息
            try:
                message = json.loads(message_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message from {queue_name}: {e}")
                return False

            # 获取处理器
            handler = QueueManager.get_handler(queue_name)
            if not handler:
                logger.error(f"No handler found for queue: {queue_name}")
                return False

            # 调用处理器
            try:
                # 检查处理器是否需要queue_name参数（模式匹配的处理器）
                import inspect
                sig = inspect.signature(handler)
                if len(sig.parameters) > 1:
                    # 模式匹配处理器，传递queue_name
                    handler(message, queue_name)
                else:
                    # 普通处理器
                    handler(message)

                QueueManager._stats["messages_processed"] += 1
                logger.debug(f"Successfully processed message from {queue_name}")
                return True

            except Exception as e:
                QueueManager._stats["process_errors"] += 1
                logger.error(f"Handler failed for queue {queue_name}: {e}", exc_info=True)
                return False

        except Exception as e:
            # 如果是连接问题，尝试重置连接
            if "Too many connections" in str(e):
                logger.warning(f"Redis connection issue in process_message, resetting client: {e}")
                QueueManager.reset_redis_client()

            logger.error(f"Failed to process message from {queue_name}: {e}")
            return False

    @staticmethod
    def start_worker(queue_names: List[str], worker_name: str = "worker") -> None:
        """启动队列工作进程

        Args:
            queue_names: 要监听的队列名称列表
            worker_name: 工作进程名称
        """
        logger.info(f"Starting worker {worker_name} for queues: {queue_names}")

        while True:
            try:
                # 轮询所有队列
                for queue_name in queue_names:
                    try:
                        QueueManager.process_message(queue_name, timeout=1)
                    except Exception as e:
                        logger.error(f"Error processing queue {queue_name}: {e}")

                # 短暂休息避免CPU占用过高
                time.sleep(0.1)

            except KeyboardInterrupt:
                logger.info(f"Worker {worker_name} stopped by user")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                time.sleep(1)  # 出错时等待更长时间

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """获取队列统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return QueueManager._stats.copy()
