import logging
from threading import Lock
from typing import List

import dramatiq
from dramatiq.worker import Worker

from common.constants import get_all_queues
from consumer.base import redis_broker
from utils.auto_import import ModuleImporter

_logger = logging.getLogger(__name__)

# module-scope state
_workers: List[Worker] = []
_workers_running: bool = False
_workers_lock = Lock()


def worker_start() -> None:
    global _workers, _workers_running
    with _workers_lock:
        if _workers_running:
            _logger.info("[worker] already running, skip start()")
            return

        _logger.info("[worker] starting...")
        # declare queues and set broker
        for q in get_all_queues():
            redis_broker.declare_queue(q)
        dramatiq.set_broker(redis_broker)
        # Ensure actors are registered (import recursively so subpackages like consumer/processors are loaded)
        ModuleImporter.import_classes(directory="consumer", recursive=True)

        workers: List[Worker] = []
        for queue in get_all_queues():
            w = Worker(
                redis_broker,
                queues=[queue],
                worker_threads=1,
                worker_timeout=1000,
            )
            workers.append(w)
        for w in workers:
            w.start()

        _workers = workers
        _workers_running = True
        _logger.info("[worker] started %d workers", len(workers))


def worker_stop() -> None:
    global _workers, _workers_running
    with _workers_lock:
        if not _workers_running:
            _logger.info("[worker] not running, skip stop()")
            return
        _logger.info("[worker] stopping...")
        try:
            for w in _workers:
                try:
                    w.stop()
                except Exception:
                    _logger.exception("[worker] stop one worker failed (ignored)")
        finally:
            _workers = []
            _workers_running = False
            _logger.info("[worker] stopped")


def worker_status() -> dict:
    return {"running": _workers_running, "count": len(_workers)}