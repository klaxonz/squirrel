from __future__ import annotations

from collections.abc import Callable

from .registry import ConsumerRegistry


def queue_listener(stream: str, group: str, consumer_name: str | None = None, *, block_ms: int = 1000, read_count: int = 1, consumer_count: int = 1) -> Callable:
    """标记函数为 MQ 消费者，并注册到注册表。"""
    def decorator(func: Callable) -> Callable:
        base = consumer_name or func.__name__
        ConsumerRegistry.register(
            stream=stream,
            group=group,
            consumer_name=base,
            handler=func,
            block_ms=block_ms,
            read_count=read_count,
            consumer_count=consumer_count,
        )
        return func
    return decorator


