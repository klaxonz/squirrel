import logging
from threading import Lock

from workers.scheduling.executors.manager import crawl_worker_start, crawl_worker_status, crawl_worker_stop

_logger = logging.getLogger(__name__)

# module-scope state
_workers_running: bool = False
_workers_lock = Lock()


def worker_start() -> None:
    """Start the crawl worker runtime.

    The old Redis-Stream queue consumer (``WorkerRunner``) was a no-op shell
    -- no listener was ever registered -- so it has been removed. Only the
    crawl worker runtime is started here.
    """
    global _workers_running
    with _workers_lock:
        if _workers_running:
            _logger.info('[worker] already running, skip start()')
            return

        _logger.info('[worker] starting...')
        crawl_worker_start()
        _workers_running = True
        _logger.info(
            '[worker] started %d crawl worker threads',
            crawl_worker_status()['count'],
        )


def worker_stop() -> None:
    """Stop the crawl worker runtime."""
    global _workers_running
    with _workers_lock:
        if not _workers_running:
            _logger.info('[worker] not running, skip stop()')
            return

        _logger.info('[worker] stopping...')
        crawl_worker_stop()

        # 设置停止标志
        _workers_running = False

        # 等待所有工作线程结束(由于使用了daemon线程,主程序退出时会自动结束)
        _logger.info('[worker] worker threads will stop when main process exits')


def worker_status() -> dict:
    crawl_status = crawl_worker_status()
    return {
        'running': _workers_running or crawl_status['running'],
        'count': crawl_status['count'],
    }
