"""Process-wide management of background daemon threads.

Background threads in this codebase run as daemons (so an ungraceful process
exit never hangs), but that alone is unsafe: a daemon thread mid-DB-write gets
killed without a chance to finish, which corrupts rows / leaves half-written
files. This module gives the scheduler / worker bootstrap a single place to:

- register threads they start (``register`` / ``start_managed``)
- signal + join every registered thread on shutdown (``shutdown_all``)

Request-scoped fire-and-forget threads (e.g. RSS status sync, background
subscription import) are intentionally NOT registered here -- they live beyond
a single request by design and must not block request handling or shutdown.

The registry is a process-wide singleton (``thread_manager``). It is cheap to
hold (just a list + lock) and tolerant of double-shutdown.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from threading import Thread

logger = logging.getLogger(__name__)

# Default per-thread join timeout during shutdown. Long enough to let a typical
# DB commit / flush finish, short enough that a wedged thread can't hang the
# process. Individual call sites can override.
DEFAULT_JOIN_TIMEOUT = 5.0


class ThreadManager:
    """Registry + graceful shutdown for managed background threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: list[Thread] = []
        self._stopped = False

    def register(self, thread: Thread) -> Thread:
        """Track an already-started thread so it can be joined on shutdown.

        The thread is expected to be a daemon that checks an external stop
        signal (Event / flag) -- :meth:`shutdown_all` only joins, it does not
        know how to ask each thread to stop (callers set the signal first).
        """
        with self._lock:
            if self._stopped:
                logger.debug('ThreadManager already stopped; not tracking %s', thread.name)
                return thread
            self._threads.append(thread)
        return thread

    def start_managed(
        self,
        target: Callable,
        *,
        name: str | None = None,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> Thread:
        """Start a daemon thread and register it in one step.

        Mirrors ``threading.Thread`` kwargs so callers swap ``Thread(...).start()``
        for ``thread_manager.start_managed(...)`` with minimal change.
        """
        thread = Thread(target=target, name=name, args=args, kwargs=kwargs or {}, daemon=True)
        thread.start()
        self.register(thread)
        return thread

    def shutdown_all(self, timeout: float = DEFAULT_JOIN_TIMEOUT) -> int:
        """Join every registered thread (up to ``timeout`` each).

        Callers MUST set the threads' stop signals *before* calling this --
        otherwise joins will block for the full ``timeout``.

        Returns the number of threads that were still alive when this returns
        (0 == clean shutdown). Safe to call multiple times.
        """
        with self._lock:
            if self._stopped:
                return 0
            self._stopped = True
            threads = list(self._threads)
            self._threads.clear()

        still_alive = 0
        for thread in threads:
            if not thread.is_alive():
                continue
            logger.debug('Joining background thread %s (timeout=%ss)', thread.name, timeout)
            thread.join(timeout=timeout)
            if thread.is_alive():
                still_alive += 1
                logger.warning('Background thread %s did not stop within %ss', thread.name, timeout)

        if still_alive:
            logger.warning('shutdown_all: %d thread(s) still alive after join', still_alive)
        else:
            logger.debug('shutdown_all: all %d thread(s) joined cleanly', len(threads))
        return still_alive

    @property
    def registered_count(self) -> int:
        with self._lock:
            return len(self._threads)


# Process-wide singleton. Both the web lifespan and the worker bootstrap share
# a process, so whoever shuts down last calls shutdown_all().
thread_manager = ThreadManager()
