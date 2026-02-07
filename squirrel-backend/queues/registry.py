from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List


@dataclass
class ConsumerSpec:
    stream: str
    group: str
    consumer_name: str
    handler: Callable
    consumer_count: int = 1
    block_ms: int = 1000
    read_count: int = 1


class ConsumerRegistry:
    _consumers: List[ConsumerSpec] = []

    @classmethod
    def register(
        cls,
        stream: str,
        group: str,
        consumer_name: str,
        handler: Callable,
        block_ms: int = 1000,
        read_count: int = 1,
        consumer_count: int = 1,
    ) -> None:
        if consumer_count < 1:
            raise ValueError("consumer_count must be >= 1")
        cls._consumers.append(
            ConsumerSpec(
                stream=stream,
                group=group,
                consumer_name=consumer_name,
                handler=handler,
                consumer_count=consumer_count,
                block_ms=block_ms,
                read_count=read_count,
            )
        )

    @classmethod
    def all(cls) -> List[ConsumerSpec]:
        return list(cls._consumers)


