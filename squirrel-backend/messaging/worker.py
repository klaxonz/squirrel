import logging
import threading
from threading import Lock

from messaging.framework.runner import WorkerRunner
from scheduling.workers.manager import crawl_worker_start, crawl_worker_status, crawl_worker_stop

_logger = logging.getLogger(__name__)

# module-scope state
_worker_threads: list[threading.Thread] = []
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
        crawl_worker_start()
        runner = WorkerRunner()
        runner.start()
        global _runner
        _runner = runner
        _worker_threads = runner.threads()
        _workers_running = True
        _logger.info(
            "[worker] started %d queue worker threads and %d crawl worker threads",
            len(_worker_threads),
            crawl_worker_status()["count"],
        )


def worker_stop() -> None:
    global _worker_threads, _workers_running
    with _workers_lock:
        if not _workers_running:
            _logger.info("[worker] not running, skip stop()")
            return

        _logger.info("[worker] stopping...")
        crawl_worker_stop()

        # 设置停止标志
        _workers_running = False

        # 等待所有工作线程结束（由于使用了daemon线程，主程序退出时会自动结束）
        _logger.info("[worker] worker threads will stop when main process exits")

        _worker_threads = []
        _logger.info("[worker] stopped")


def worker_status() -> dict:
    crawl_status = crawl_worker_status()
    return {
        "running": _workers_running or crawl_status["running"],
        "count": len(_worker_threads) + crawl_status["count"],
    }
