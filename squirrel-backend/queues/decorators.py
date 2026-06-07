from __future__ import annotations

from collections.abc import Callable

from .registry import ConsumerRegistry


def queue_listener(stream: str, group: str, consumer_name: str | None = None, *, block_ms: int = 1000, read_count: int = 1, consumer_count: int = 1) -> Callable:
    """Mark the function as an MQ consumer and register it with the registry."""
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


