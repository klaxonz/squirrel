from __future__ import annotations

import threading


class WorkerRunner:
    """No-op queue worker runner.

    The Redis-Stream consumer half of the message queue was never wired to any
    handler in production (no ``@queue_listener`` was ever registered, and the
    old ``start()`` imported a ``messaging.handlers`` package that did not
    exist). The producer half (``RedisStreamProducer``) remains live. The crawl
    workers are started separately by ``crawl_worker_start`` in
    ``workers/messaging/worker.py``, so this runner no longer spawns anything.
    It is retained as a no-op so the worker process entrypoint and its test
    stay unchanged.
    """

    def __init__(self):
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        # Intentionally empty: see class docstring.
        return

    def threads(self) -> list[threading.Thread]:
        return self._threads
