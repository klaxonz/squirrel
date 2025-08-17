from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass
class ConsumerSpec:
    stream: str
    group: str
    consumer_name: str
    handler: Callable
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
        if consumer_count == 1:
            cls._consumers.append(ConsumerSpec(stream, group, consumer_name, handler, block_ms, read_count))
        else:
            base = consumer_name
            for i in range(1, consumer_count + 1):
                cls._consumers.append(ConsumerSpec(stream, group, f"{base}-{i}", handler, block_ms, read_count))

    @classmethod
    def all(cls) -> List[ConsumerSpec]:
        return list(cls._consumers)


