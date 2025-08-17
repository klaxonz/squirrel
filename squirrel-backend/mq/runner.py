from __future__ import annotations

import threading
from typing import List

from .consumer import RedisStreamConsumer, ConsumerOptions
from .registry import ConsumerRegistry
from utils.auto_import import ModuleImporter


class WorkerRunner:
    def __init__(self):
        self._threads: List[threading.Thread] = []

    def start(self) -> None:
        # 自动导入 consumer 包（包含 processors），触发装饰器注册
        ModuleImporter.import_classes(directory="consumer", recursive=True)

        consumers: List[RedisStreamConsumer] = []
        for spec in ConsumerRegistry.all():
            options = ConsumerOptions(
                group=spec.group,
                consumer_name=spec.consumer_name,
                block_ms=spec.block_ms,
                read_count=spec.read_count,
            )
            consumers.append(RedisStreamConsumer(spec.stream, spec.handler, options))

        for c in consumers:
            thread_name = f"mq-{c.stream}-{c.options.group}-{c.options.consumer_name}"
            t = threading.Thread(target=c.start_loop, daemon=True, name=thread_name)
            t.start()
            self._threads.append(t)

    def threads(self) -> List[threading.Thread]:
        return self._threads


