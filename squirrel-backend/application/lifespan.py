import logging
import signal
import threading
from contextlib import contextmanager

from application.runtime_setup import (
    apply_site_config,
    configure_cloudflare_bypass,
    configure_cookie_resolvers,
    prepare_youtube_oauth_env,
    start_site_runtimes,
)
from infrastructure.config.startup_dependencies import (
    clear_optional_startup_issue,
    record_optional_startup_issue,
    reset_startup_dependency_issues,
)
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
    except Exception:
        logger.exception("[%s] Database upgrade failed", component)
        raise

    try:
        apply_site_config()
    except Exception:
        logger.exception("[%s] Failed to apply site config overrides", component)
        raise

    # Cloudflare bypass is optional; cookie resolver is required.
    try:
        configure_cloudflare_bypass()
        clear_optional_startup_issue("cloudflare_bypass")
    except Exception as exc:
        record_optional_startup_issue("cloudflare_bypass", exc)
        logger.warning("[%s] Failed to configure Cloudflare bypass client: %s", component, exc)
    try:
        configure_cookie_resolvers()
    except Exception:
        logger.exception("[%s] Failed to configure cookie resolver", component)
        raise

    try:
        prepare_youtube_oauth_env()
        start_site_runtimes()
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
        except Exception:
            logger.warning("[%s] Failed to recover stale sync states", component, exc_info=True)
        start_reload_listener(component)
    except Exception:
        logger.exception("[%s] Runtime bootstrap failed", component)
        raise

    try:
        yield
    finally:
        try:
            stop_reload_listener(component)
        except Exception:
            logger.warning("[%s] Failed to stop reload listener", component, exc_info=True)
        try:
            from infrastructure.site_runtimes.manager import shutdown_site_runtimes
            shutdown_site_runtimes()
        except Exception:
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



