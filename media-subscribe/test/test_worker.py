import dramatiq
import time
import signal
import sys
import importlib
import pkgutil
import os
from dramatiq.worker import Worker

from common import constants
from consumer.base import redis_broker


def auto_discover_actors(package_name='consumer'):
    """自动发现和导入所有的 actors"""
    package = importlib.import_module(package_name)

    print(f"Discovering actors in package: {package_name}")

    for _, name, _ in pkgutil.iter_modules([os.path.dirname(package.__file__)]):
        if name != 'base':  # 跳过 base.py
            module_name = f'{package_name}.{name}'
            print(f"Importing module: {module_name}")
            importlib.import_module(module_name)


def create_worker():
    # 先声明队列
    redis_broker.declare_queue(constants.QUEUE_SUBSCRIBE_TASK)
    redis_broker.declare_queue(constants.QUEUE_DOWNLOAD_TASK)
    redis_broker.declare_queue(constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD)
    redis_broker.declare_queue(constants.QUEUE_VIDEO_PROGRESS_TASK)

    print(f"Broker middleware: {redis_broker.middleware}")
    print(f"Target queues: {redis_broker.queues}")

    # 设置全局 broker
    dramatiq.set_broker(redis_broker)

    # 自动发现和导入 actors
    auto_discover_actors()

    # 创建 worker 实例
    worker = Worker(
        redis_broker,
        queues=[constants.QUEUE_SUBSCRIBE_TASK],
        worker_threads=4,
        worker_timeout=1000,
    )

    # 打印已注册的 actors
    print(f"Registered actors: {redis_broker.actors}")
    return worker


def run_worker():
    worker = create_worker()

    def signal_handler(signum, frame):
        print("Stopping worker...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Starting worker...")
    worker.start()

    try:
        print("Worker running, waiting for messages...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping worker...")
        worker.stop()


if __name__ == "__main__":
    run_worker()
