from __future__ import annotations

from typing import Callable, Optional

from .registry import ConsumerRegistry


def queue_listener(stream: str, group: str, consumer_name: Optional[str] = None, *, block_ms: int = 1000, read_count: int = 1, consumer_count: int = 1) -> Callable:
    """标记函数为 MQ 消费者，并注册到注册表。"""
    def decorator(func: Callable) -> Callable:
        base = consumer_name or func.__name__
        if consumer_count < 1:
            raise ValueError("consumer_count must be >= 1")
        if consumer_count == 1:
            ConsumerRegistry.register(stream, group, base, func, block_ms=block_ms, read_count=read_count)
        else:
            for i in range(1, consumer_count + 1):
                ConsumerRegistry.register(stream, group, f"{base}-{i}", func, block_ms=block_ms, read_count=read_count)
        return func
    return decorator


