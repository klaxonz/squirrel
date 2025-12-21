import logging
import signal
import threading
from contextlib import contextmanager

from common.log import init_logging
from core.site_config_manager import apply_site_config_overrides
from mq.queue_config import ensure_queue_config_initialized
from plugins.loader import init_plugins, app_start, app_stop

logger = logging.getLogger(__name__)


@contextmanager
def bootstrap_runtime(component: str):
    """
    Initialize shared runtime pieces (logging, plugins, queue config, hooks)
    for standalone worker/scheduler processes.
    """
    init_logging()
    logger.info("[%s] Bootstrapping runtime...", component)

    try:
        apply_site_config_overrides()
    except Exception as exc:
        logger.warning("[%s] Failed to apply site config overrides: %s", component, exc)

    try:
        from crawl import configure_cloudflare_bypass_client
        from utils.cloudflare_bypass import get_default_client
        configure_cloudflare_bypass_client(get_default_client())
        logger.info("[%s] Cloudflare bypass client configured", component)
    except Exception as exc:
        logger.warning("[%s] Failed to configure Cloudflare bypass client: %s", component, exc)

    try:
        init_plugins()
        ensure_queue_config_initialized()
        app_start()
    except Exception:
        logger.exception("[%s] Runtime bootstrap failed", component)
        raise

    try:
        yield
    finally:
        try:
            app_stop()
        except Exception:
            logger.warning("[%s] Plugin shutdown failed", component, exc_info=True)


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

