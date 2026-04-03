import logging
import signal
import threading
from contextlib import contextmanager

from common.log import init_logging
from core.site_config_manager import apply_site_config_overrides
from core.database_upgrade import upgrade_database
from plugins.manager import bootstrap_plugin_runtime, shutdown_plugin_runtime
from plugins.reload_listener import start_reload_listener, stop_reload_listener
from utils.cookie import resolve_cookie_file_for_url
from utils.runtime_http import set_cloudflare_bypass_client
from utils.runtime_http import set_cookie_file_resolver

logger = logging.getLogger(__name__)


@contextmanager
def bootstrap_runtime(component: str):
    """
    Initialize shared runtime pieces (logging, plugin runtime manager)
    for standalone worker/scheduler processes.
    """
    init_logging()
    logger.info("[%s] Bootstrapping runtime...", component)

    try:
        upgrade_database()
    except Exception:
        logger.exception("[%s] Database upgrade failed", component)
        raise

    try:
        apply_site_config_overrides()
    except Exception as exc:
        logger.warning("[%s] Failed to apply site config overrides: %s", component, exc)

    try:
        from utils.cloudflare_bypass import get_default_client
        set_cloudflare_bypass_client(get_default_client())
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        logger.info("[%s] Cloudflare bypass client configured", component)
    except Exception as exc:
        logger.warning("[%s] Failed to configure Cloudflare bypass client: %s", component, exc)

    try:
        bootstrap_plugin_runtime()
        try:
            from services import subscription_sync_state_service
            drained_result = subscription_sync_state_service.reconcile_terminal_drained_sync_states()
            queued_result = subscription_sync_state_service.recover_stale_queued_sync_states()
            running_result = subscription_sync_state_service.recover_stale_running_sync_states()
            if drained_result.get('completed') or drained_result.get('failed') or queued_result.get('recovered') or running_result.get('recovered'):
                logger.info(
                    "[%s] Recovered sync states: drained_completed=%s drained_failed=%s queued=%s running=%s",
                    component,
                    drained_result.get('completed', 0),
                    drained_result.get('failed', 0),
                    queued_result.get('recovered', 0),
                    running_result.get('recovered', 0),
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
            shutdown_plugin_runtime()
        except Exception:
            logger.warning("[%s] Plugin runtime shutdown failed", component, exc_info=True)


def create_shutdown_event(component: str) -> threading.Event:
    """
    Register signal handlers and return an Event that flips when shutdown is requested.
    """
    event = threading.Event()

    def _handle(sig, _frame):
        logger.info("[%s] Received signal %s, shutting down...", component, sig)
        event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle)

    return event


def wait_for_shutdown(event: threading.Event):
    """
    Block until shutdown_event is set.
    """
    try:
        while not event.is_set():
            event.wait(timeout=1.0)
    except KeyboardInterrupt:
        event.set()

