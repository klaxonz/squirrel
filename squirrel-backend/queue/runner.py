from __future__ import annotations

import threading
from typing import List
from utils import module_discovery
from .consumer import RedisStreamConsumer, ConsumerOptions
from .registry import ConsumerRegistry


class WorkerRunner:
    def __init__(self):
        self._threads: List[threading.Thread] = []

    def start(self) -> None:
        # 1. 导入所有 processor 模块（注册 @mq_consumer 装饰的消费者）
        module_discovery.import_classes_from_package(package="consumer", recursive=True)
        
        # 2. 配置并注册域消费者
        from consumer.consumers_setup import setup_all_consumers
        from queue.consumer_config import init_domain_consumers
        
        setup_all_consumers()
        init_domain_consumers()

        # 3. 启动所有已注册的消费者
        consumers: List[RedisStreamConsumer] = []
        for spec in ConsumerRegistry.all():
            options = ConsumerOptions(
                group=spec.group,
                consumer_name=spec.consumer_name,
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

    def threads(self) -> List[threading.Thread]:
        return self._threads
