import logging
import threading
from threading import Lock
from typing import List

from queues.runner import WorkerRunner

_logger = logging.getLogger()

# module-scope state
_worker_threads: List[threading.Thread] = []
_workers_running: bool = False
_workers_lock = Lock()
_runner: WorkerRunner | None = None


def worker_start() -> None:
    global _worker_threads, _workers_running
    with _workers_lock:
        if _workers_running:
            _logger.info("[worker] already running, skip start()")
            return

        _logger.info("[worker] starting...")
        runner = WorkerRunner()
        runner.start()
        global _runner
        _runner = runner
        _worker_threads = runner.threads()
        _workers_running = True
        _logger.info("[worker] started %d worker threads", len(_worker_threads))


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