from __future__ import annotations

import logging
import threading

from core.config import settings
from utils import module_discovery

from .consumer import ConsumerOptions, RedisStreamConsumer
from .registry import ConsumerRegistry


class WorkerRunner:
    def __init__(self):
        self._threads: list[threading.Thread] = []
        self._logger = logging.getLogger(__name__)

    def _parse_consumer_count_overrides(self) -> tuple[dict[str, int], list[tuple[str, int]]]:
        exact: dict[str, int] = {}
        prefixes: list[tuple[str, int]] = []

        raw = (settings.MQ_CONSUMER_COUNT_OVERRIDES or "").strip()
        if not raw:
            return exact, prefixes

        for token in raw.replace(";", ",").split(","):
            token = token.strip()
            if not token:
                continue
            if "=" not in token:
                self._logger.warning("Invalid MQ override token (missing '='): %s", token)
                continue
            pattern, count_str = token.rsplit("=", 1)
            pattern = pattern.strip()
            count_str = count_str.strip()

            try:
                count = int(count_str)
            except ValueError:
                self._logger.warning("Invalid MQ override token (count is not int): %s", token)
                continue

            if count < 1:
                self._logger.warning("Invalid MQ override token (count < 1): %s", token)
                continue

            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if not prefix:
                    self._logger.warning("Invalid MQ override token (empty prefix): %s", token)
                    continue
                prefixes.append((prefix, count))
            else:
                exact[pattern] = count

        prefixes.sort(key=lambda x: len(x[0]), reverse=True)
        return exact, prefixes

    def _resolve_consumer_count(self, stream: str, configured_count: int, *, exact: dict[str, int], prefixes: list[tuple[str, int]]) -> int:
        count = configured_count if configured_count != 1 else settings.MQ_CONSUMER_DEFAULT_COUNT
        if stream in exact:
            return exact[stream]
        for prefix, override_count in prefixes:
            if stream.startswith(prefix):
                return override_count
        return max(1, count)

    def start(self) -> None:
        # 1. 导入所有 processor 模块（注册 @queue_listener 装饰的消费者）
        module_discovery.import_classes_from_package(
            package="messaging.handlers",
            recursive=True,
        )

        # 2. 启动所有已注册的消费者
        exact, prefixes = self._parse_consumer_count_overrides()
        consumers: list[RedisStreamConsumer] = []
        for spec in ConsumerRegistry.all():
            consumer_count = self._resolve_consumer_count(
                spec.stream,
                spec.consumer_count,
                exact=exact,
                prefixes=prefixes,
            )
            consumer_names = (
                [spec.consumer_name]
                if consumer_count == 1
                else [f"{spec.consumer_name}-{i}" for i in range(1, consumer_count + 1)]
            )

            for consumer_name in consumer_names:
                options = ConsumerOptions(
                    group=spec.group,
                    consumer_name=consumer_name,
                    block_ms=spec.block_ms,
                    read_count=spec.read_count,
                    retry_dlq=f"{spec.stream}:dlq",
                    max_delivery=3,
                )
                consumers.append(RedisStreamConsumer(spec.stream, spec.handler, options))

        for c in consumers:
            thread_name = f"mq-{c.stream}-{c.options.group}-{c.options.consumer_name}"
            t = threading.Thread(target=c.start_loop, daemon=True, name=thread_name)
            t.start()
            self._threads.append(t)

    def threads(self) -> list[threading.Thread]:
        return self._threads
