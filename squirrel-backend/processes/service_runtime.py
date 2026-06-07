import logging
import os
import signal
import threading
from contextlib import contextmanager

from common.log import init_logging
from core.database_upgrade import upgrade_database
from core.site_config_manager import apply_site_config_overrides
from core.startup_dependencies import (
    clear_optional_startup_issue,
    record_optional_startup_issue,
    reset_startup_dependency_issues,
)
from site_runtimes.manager import bootstrap_site_runtimes, shutdown_site_runtimes
from site_runtimes.reload_listener import start_reload_listener, stop_reload_listener
from utils.cookie import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
from utils.runtime_http import set_cloudflare_bypass_client, set_cookie_domain_resolver, set_cookie_file_resolver

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

    try:
        apply_site_config_overrides()
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("[%s] Failed to apply site config overrides", component)
        raise

    try:
        from utils.cloudflare_bypass import get_default_client
        set_cloudflare_bypass_client(get_default_client())
        clear_optional_startup_issue("cloudflare_bypass")
        logger.info("[%s] Cloudflare bypass client configured", component)
    except Exception as exc:  # startup/shutdown boundary -- prevent crash during lifecycle
        record_optional_startup_issue("cloudflare_bypass", exc)
        logger.warning("[%s] Failed to configure Cloudflare bypass client: %s", component, exc)
    try:
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
        logger.info("[%s] Cookie resolver configured", component)
    except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
        logger.exception("[%s] Failed to configure cookie resolver", component)
        raise

    try:
        from services.youtube_oauth_service import get_oauth_credentials_for_daemon
        oauth_file = get_oauth_credentials_for_daemon()
        if oauth_file:
            os.environ["YOUTUBE_OAUTH_STATE_FILE"] = oauth_file
        bootstrap_site_runtimes()
        try:
            from services import video_extraction_projection_service
            rebuilt_count = video_extraction_projection_service.ensure_projection_seeded()
            logger.info("[%s] Video extraction projection ready (rebuilt=%s)", component, rebuilt_count)
        except Exception:  # startup/shutdown boundary -- prevent crash during lifecycle
            logger.exception("[%s] Failed to seed video extraction projection", component)
            raise
        try:
            from services import subscription_sync_state_service
            drained_result = subscription_sync_state_service.reconcile_terminal_drained_sync_states()
            queued_result = subscription_sync_state_service.recover_stale_queued_sync_states()
            running_result = subscription_sync_state_service.recover_stale_running_sync_states()
            retry_wait_result = subscription_sync_state_service.reconcile_retry_wait_run_projections()
            if (
                drained_result.get("completed")
                or drained_result.get("failed")
                or queued_result.get("recovered")
                or running_result.get("recovered")
                or retry_wait_result.get("repaired")
            ):
                logger.info(
                    "[%s] Recovered sync states: drained_completed=%s drained_failed=%s queued=%s running=%s retry_wait=%s",
                    component,
                    drained_result.get("completed", 0),
                    drained_result.get("failed", 0),
                    queued_result.get("recovered", 0),
                    running_result.get("recovered", 0),
                    retry_wait_result.get("repaired", 0),
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



