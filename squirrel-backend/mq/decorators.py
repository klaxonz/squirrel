from __future__ import annotations

from typing import Callable, Optional

from .registry import ConsumerRegistry


def mq_consumer(stream: str, group: str, consumer_name: Optional[str] = None, *, block_ms: int = 1000, read_count: int = 1) -> Callable:
    """标记函数为 MQ 消费者，并注册到注册表。

    业务层在 processors/* 中使用此装饰器，不关心 MQ 细节。
    """
    def decorator(func: Callable) -> Callable:
        name = consumer_name or func.__name__
        ConsumerRegistry.register(stream, group, name, func, block_ms=block_ms, read_count=read_count)
        return func
    return decorator


