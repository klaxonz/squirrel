import logging
import os
import socket
import threading
from threading import Lock
from uuid import uuid4

from domains.subscription.application.services.core.update.task_progress_service import (
    SubscriptionSyncTaskProgressService,
)
from domains.subscription.application.services.crawl.executors.subscription_import_executor import (
    SubscriptionImportExecutor,
)
from domains.subscription.application.services.crawl.executors.subscription_sync_executor import (
    CrawlExecutorService as SubscriptionSyncExecutor,
)
from domains.subscription.application.services.crawl.executors.video_extract_executor import (
    CrawlExecutorService as VideoExtractExecutor,
)
from domains.subscription.application.services.service import SubscriptionService
from domains.video.application.services.extraction.progress_service import VideoExtractionProgressService
from infrastructure.concurrency.thread_manager import thread_manager
from infrastructure.config.settings import settings
from workers.scheduling.executors.runtime import CrawlWorkerRuntime

_logger = logging.getLogger(__name__)

_worker_threads: list[threading.Thread] = []
_workers_running: bool = False
_workers_lock = Lock()
_stop_event: threading.Event | None = None

def _create_runtime(*, worker_id: str) -> tuple[CrawlWorkerRuntime, SubscriptionService]:
    services = SubscriptionService()
    runtime = CrawlWorkerRuntime(
        worker_id=worker_id,
        max_concurrency=max(1, int(settings.crawl.slots_per_process)),
        poll_interval_seconds=settings.crawl.worker_poll_interval_ms / 1000.0,
        subscription_task_progress=SubscriptionSyncTaskProgressService(services.lifecycle),
        video_extraction_progress=VideoExtractionProgressService(services.lifecycle),
        subscription_sync_executor=SubscriptionSyncExecutor(
            lifecycle=services.lifecycle,
            orchestrator_service=services.orchestrator,
            subscription_svc=services.crud,
        ),
        subscription_import_executor=SubscriptionImportExecutor(services.import_service),
        video_extract_executor=VideoExtractExecutor(services.video_service.extraction),
    )
    return runtime, services


def _run_runtime(runtime: CrawlWorkerRuntime, services: SubscriptionService, stop_event: threading.Event) -> None:
    try:
        runtime.run_loop(stop_event)
    finally:
        services.close()


def crawl_worker_start() -> None:
    global _worker_threads, _workers_running, _stop_event
    with _workers_lock:
        if _workers_running:
            _logger.info('[crawl-worker] already running, skip start()')
            return

        _stop_event = threading.Event()
        runtime, services = _create_runtime(
            worker_id=f'{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:12]}',
        )
        thread = threading.Thread(
            target=_run_runtime,
            args=(runtime, services, _stop_event),
            daemon=True,
            name='crawl-runtime-1',
        )
        thread.start()
        thread_manager.register(thread)

        _worker_threads = [thread]
        _workers_running = True
        _logger.info('[crawl-worker] started %d worker threads', len(_worker_threads))


def crawl_worker_stop() -> None:
    global _worker_threads, _workers_running, _stop_event
    with _workers_lock:
        if not _workers_running:
            _logger.info('[crawl-worker] not running, skip stop()')
            return
        # Signal the run loop to exit; the actual thread join happens at
        # process shutdown via thread_manager.shutdown_all() so in-flight
        # tasks get a bounded chance to finish instead of being killed.
        if _stop_event is not None:
            _stop_event.set()
        _worker_threads = []
        _stop_event = None
        _workers_running = False
        _logger.info('[crawl-worker] stopped')


def crawl_worker_status() -> dict:
    return {'running': _workers_running, 'count': len(_worker_threads)}
