"""Tests for the process-wide ThreadManager shutdown coordination."""

import threading
import time

from infrastructure.concurrency.thread_manager import ThreadManager


def test_start_managed_registers_and_runs_daemon_thread():
    started = threading.Event()
    manager = ThreadManager()

    def worker():
        started.set()

    t = manager.start_managed(worker, name='test-worker')
    assert started.wait(timeout=2)
    assert t.daemon is True
    assert manager.registered_count == 1
    t.join(timeout=2)


def test_shutdown_all_joins_live_threads_after_stop_signal():
    manager = ThreadManager()
    stop = threading.Event()
    finished = threading.Event()

    def worker():
        while not stop.is_set():
            time.sleep(0.01)
        finished.set()

    t = manager.start_managed(worker, name='loop-worker')
    # Give the loop a moment to be running.
    time.sleep(0.05)
    assert t.is_alive()

    stop.set()
    still_alive = manager.shutdown_all(timeout=2)

    assert still_alive == 0
    assert finished.is_set()
    assert not t.is_alive()


def test_shutdown_all_is_idempotent():
    manager = ThreadManager()
    manager.start_managed(lambda: None, name='quick')
    time.sleep(0.05)
    assert manager.shutdown_all() == 0
    # Second call is a no-op (returns 0, no error).
    assert manager.shutdown_all() == 0


def test_shutdown_all_reports_threads_that_do_not_finish():
    manager = ThreadManager()
    stop = threading.Event()

    def worker():
        while not stop.is_set():
            time.sleep(0.01)

    manager.start_managed(worker, name='stubborn')
    time.sleep(0.05)
    # Deliberately do NOT set the stop signal -> join times out.
    still_alive = manager.shutdown_all(timeout=0.2)
    assert still_alive == 1
    # Clean up the leaked thread.
    stop.set()


def test_register_after_shutdown_is_ignored():
    manager = ThreadManager()
    manager.shutdown_all()
    t = manager.start_managed(lambda: None, name='too-late')
    # Registered-after-stop threads are not tracked, so count stays 0.
    assert manager.registered_count == 0
    t.join(timeout=2)
