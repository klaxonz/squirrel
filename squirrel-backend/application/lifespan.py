import logging
import signal
import threading
from contextlib import contextmanager

from application.runtime_setup import (
    apply_site_config,
    bootstrap_site_runtimes_with_oauth,
    configure_runtime_http,
)
from infrastructure.config.startup_dependencies import reset_startup_dependency_issues
from infrastructure.database.migrations import upgrade_database
from infrastructure.site_runtimes.reload_listener import start_reload_listener, stop_reload_listener
from shared_kernel.infrastructure.log import init_logging

logger = logging.getLogger(__name__)


@contextmanager
def bootstrap_runtime(component: str):
    """Initialize shared runtime pieces (logging, site runtime manager)
    for standalone worker/scheduler processes.
    """
    init_logging()
    logger.info("[%s] Bootstrapping runtime...", component)
    reset_startup_dependency_issues()

    try:
        upgrade_database()
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("[%s] Database upgrade failed", component)
        raise

    apply_site_config(component)
    configure_runtime_http(component)

    try:
        bootstrap_site_runtimes_with_oauth(component)
        try:
            import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
            drained_result = subscription_sync_state_service.reconcile_terminal_drained_sync_states()
            queued_result = subscription_sync_state_service.recover_stale_queued_sync_states()
            running_result = subscription_sync_state_service.recover_stale_running_sync_states()
            if (
                drained_result.get("completed")
                or drained_result.get("failed")
                or queued_result.get("recovered")
                or running_result.get("recovered")
            ):
                logger.info(
                    "[%s] Recovered sync states: drained_completed=%s drained_failed=%s queued=%s running=%s",
                    component,
                    drained_result.get("completed", 0),
                    drained_result.get("failed", 0),
                    queued_result.get("recovered", 0),
                    running_result.get("recovered", 0),
                )
        except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
            logger.warning("[%s] Failed to recover stale sync states", component, exc_info=True)
        start_reload_listener(component)
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("[%s] Runtime bootstrap failed", component)
        raise

    try:
        yield
    finally:
        try:
            stop_reload_listener(component)
        except Exception:  # cleanup during shutdown -- must not propagate
            logger.warning("[%s] Failed to stop reload listener", component, exc_info=True)
        try:
            from infrastructure.site_runtimes.manager import shutdown_site_runtimes
            shutdown_site_runtimes()
        except Exception:  # cleanup during shutdown -- must not propagate
            logger.warning("[%s] Site runtime shutdown failed", component, exc_info=True)


def create_shutdown_event(component: str) -> threading.Event:
    """Register signal handlers and return an Event that flips when shutdown is requested.
    """
    event = threading.Event()

    def _handle(sig, _frame):
        logger.info("[%s] Received signal %s, shutting down...", component, sig)
        event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle)

    return event


def wait_for_shutdown(event: threading.Event):
    """Block until shutdown_event is set.
    """
    try:
        while not event.is_set():
            event.wait(timeout=1.0)
    except KeyboardInterrupt:
        event.set()



