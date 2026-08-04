import time

import pytest

from shared_kernel.infrastructure.deadline import DeadlineExceeded, run_with_deadline


def _echo(value):
    return value


def _sleep_then(seconds, value):
    time.sleep(seconds)
    return value


def _boom(message):
    raise RuntimeError(message)


def test_run_with_deadline_returns_callable_result():
    assert run_with_deadline(_echo, ('ok',), timeout_seconds=5) == 'ok'


def test_run_with_deadline_kills_slow_call_and_raises_deadline_exceeded():
    with pytest.raises(DeadlineExceeded):
        run_with_deadline(_sleep_then, (5.0, 'late'), timeout_seconds=0.5)


def test_run_with_deadline_surfaces_child_exceptions():
    with pytest.raises(RuntimeError, match='boom'):
        run_with_deadline(_boom, ('boom',), timeout_seconds=5)
