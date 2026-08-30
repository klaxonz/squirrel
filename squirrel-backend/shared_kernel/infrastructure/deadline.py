"""Run a callable in a spawned subprocess with a hard deadline.

Defense-in-depth for crawl operations whose worst case is a wedged HTTP
call: the callable runs in a child process and is terminated (then killed)
when it exceeds ``timeout_seconds``. In-process direct calls are the norm;
this utility is for the few operations where a hard kill matters.

The callable and its args must be importable/picklable: under the ``spawn``
start method the child is a fresh interpreter, so pass top-level functions
(or functions whose module is importable) and JSON-ish arguments.

Exceptions raised by the callable are preserved across the boundary when
they pickle cleanly (the parent re-raises the original exception type, so
callers' ``except`` clauses work as if the call were in-process). Exceptions
that cannot be pickled degrade to a ``RuntimeError`` carrying the original
type name and message.
"""

from __future__ import annotations

import multiprocessing
from queue import Empty
from typing import Any


class DeadlineExceeded(TimeoutError):
    """The callable did not finish within its deadline and was killed."""

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(f'Call exceeded its {timeout_seconds:.3f}s deadline and was killed')
        self.timeout_seconds = timeout_seconds


class _ChildProcessExited(RuntimeError):
    """The child process died before returning a result."""


class _ChildResult:
    __slots__ = ('value',)

    def __init__(self, value: Any) -> None:
        self.value = value


class _ChildFailure:
    __slots__ = ('exception',)

    def __init__(self, exception: BaseException) -> None:
        self.exception = exception


def _child_runner(target, args, kwargs, queue) -> None:  # pragma: no cover - runs in child
    try:
        value = target(*args, **kwargs)
    except BaseException as exc:
        try:
            queue.put(_ChildFailure(exc))
        except Exception:  # exception not picklable: degrade to a plain RuntimeError
            queue.put(_ChildFailure(RuntimeError(f'{type(exc).__name__}: {exc}')))
    else:
        queue.put(_ChildResult(value))


def _make_context():
    try:
        return multiprocessing.get_context('spawn')
    except ValueError:  # pragma: no cover - non-Windows fallback
        return multiprocessing.get_context()


def run_with_deadline(target, args=(), kwargs=None, *, timeout_seconds: float) -> Any:
    """Execute ``target(*args, **kwargs)`` in a subprocess; enforce the deadline.

    Returns the callable's return value. Raises :class:`DeadlineExceeded` when
    the deadline passes (the child is terminated, then killed). Exceptions the
    callable raises are re-raised in the parent when picklable, otherwise as
    ``RuntimeError``; a child that dies without a result raises
    ``RuntimeError``.
    """
    timeout_seconds = max(0.001, float(timeout_seconds))
    context = _make_context()
    queue = context.Queue()
    process = context.Process(
        target=_child_runner,
        args=(target, tuple(args), dict(kwargs or {}), queue),
        daemon=True,
    )
    process.start()
    try:
        try:
            message = queue.get(timeout=timeout_seconds)
        except Empty:
            if not process.is_alive():
                raise _ChildProcessExited('Child process exited without returning a result')
            process.terminate()
            process.join(timeout=5.0)
            if process.is_alive():
                process.kill()
                process.join(timeout=2.0)
            raise DeadlineExceeded(timeout_seconds)
        if isinstance(message, _ChildFailure):
            raise message.exception
        return message.value
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=2.0)
            if process.is_alive():
                process.kill()
        with _suppress_all():
            queue.cancel_join_thread()
            queue.close()
            queue.join_thread()


class _suppress_all:
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return True
