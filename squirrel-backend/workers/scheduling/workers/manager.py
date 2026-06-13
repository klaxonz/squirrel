import logging
import threading
from threading import Lock

from infrastructure.config.settings import settings
from workers.scheduling.workers.runtime import CrawlWorkerRuntime

_logger = logging.getLogger(__name__)

_worker_threads: list[threading.Thread] = []
_workers_running: bool = False
_workers_lock = Lock()
_stop_event: threading.Event | None = None


def crawl_worker_start() -> None:
    global _worker_threads, _workers_running, _stop_event
    with _workers_lock:
        if _workers_running:
            _logger.info("[crawl-worker] already running, skip start()")
            return

        _stop_event = threading.Event()
        runtime = CrawlWorkerRuntime(
            worker_id="crawl-runtime-1",
            max_concurrency=max(1, int(settings.CRAWL_SLOTS_PER_PROCESS)),
            poll_interval_seconds=settings.CRAWL_WORKER_POLL_INTERVAL_MS / 1000.0,
        )
        thread = threading.Thread(
            target=runtime.run_loop,
            args=(_stop_event,),
            daemon=True,
            name="crawl-runtime-1",
        )
        thread.start()

        _worker_threads = [thread]
        _workers_running = True
        _logger.info("[crawl-worker] started %d worker threads", len(_worker_threads))


def crawl_worker_stop() -> None:
    global _worker_threads, _workers_running, _stop_event
    with _workers_lock:
        if not _workers_running:
            _logger.info("[crawl-worker] not running, skip stop()")
            return
        if _stop_event is not None:
            _stop_event.set()
        _worker_threads = []
        _stop_event = None
        _workers_running = False
        _logger.info("[crawl-worker] stopped")


def crawl_worker_status() -> dict:
    return {"running": _workers_running, "count": len(_worker_threads)}
