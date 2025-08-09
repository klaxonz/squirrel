import logging
import threading
from threading import Lock
from typing import List

from common.constants import get_all_queues
from consumer.queue_management.manager import QueueManager
from utils.auto_import import ModuleImporter

_logger = logging.getLogger(__name__)

# module-scope state
_worker_threads: List[threading.Thread] = []
_workers_running: bool = False
_workers_lock = Lock()


def worker_start() -> None:
    global _worker_threads, _workers_running
    with _workers_lock:
        if _workers_running:
            _logger.info("[worker] already running, skip start()")
            return

        _logger.info("[worker] starting...")

        # 确保处理器被注册（递归导入consumer目录下的所有模块）
        ModuleImporter.import_classes(directory="consumer", recursive=True)

        # 为每个队列创建工作线程
        worker_threads: List[threading.Thread] = []
        queues = get_all_queues()

        for queue in queues:
            thread = threading.Thread(
                target=QueueManager.start_worker,
                args=([queue], f"worker-{queue}"),
                daemon=True,
                name=f"worker-{queue}"
            )
            worker_threads.append(thread)
            thread.start()

        _worker_threads = worker_threads
        _workers_running = True
        _logger.info("[worker] started %d worker threads", len(worker_threads))


def worker_stop() -> None:
    global _worker_threads, _workers_running
    with _workers_lock:
        if not _workers_running:
            _logger.info("[worker] not running, skip stop()")
            return
        _logger.info("[worker] stopping...")

        # 设置停止标志
        _workers_running = False

        # 等待所有工作线程结束（由于使用了daemon线程，主程序退出时会自动结束）
        _logger.info("[worker] worker threads will stop when main process exits")

        _worker_threads = []
        _logger.info("[worker] stopped")


def worker_status() -> dict:
    return {"running": _workers_running, "count": len(_worker_threads)}