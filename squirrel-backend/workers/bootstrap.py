"""Worker process bootstrap: runtime initialization + shutdown coordination.

Used by standalone worker/scheduler processes (``workers/messaging/process.py``,
``workers/scheduling/process.py``). This is the sync counterpart to the FastAPI
lifespan in ``main.py`` — both initialize the same shared runtime (logging, db,
site config, http, site plugins), but worker processes are plain Python scripts
without a FastAPI app, so they use a sync context manager instead.
"""
import logging
import os
import signal
import threading
from contextlib import contextmanager

from infrastructure.config.settings import settings
from infrastructure.database.migrations import upgrade_database
from infrastructure.runtime.site_config_manager import apply_site_config_overrides
from infrastructure.site_catalog.cookies import resolve_cookie_file_for_url, resolve_cookie_match_domain_for_url
from infrastructure.site_catalog.runtime_http import (
    set_cloudflare_bypass_client,
    set_cookie_domain_resolver,
    set_cookie_file_resolver,
)
from infrastructure.site_plugins.registry import get_site_plugin_registry
from shared_kernel.infrastructure.log import init_logging

logger = logging.getLogger(__name__)


@contextmanager
def bootstrap_runtime(component: str):
    """Initialize shared runtime for a standalone worker/scheduler process.

    ``component`` is a short label (e.g. 'worker', 'scheduler') used in log lines.
    """
    init_logging()
    logger.info("[%s] Bootstrapping runtime...", component)

    for notice in settings.optional_feature_warnings():
        logger.warning("[%s] %s", component, notice)

    try:
        upgrade_database()
    except Exception:
        logger.exception("[%s] Database upgrade failed", component)
        raise

    try:
        apply_site_config_overrides()
    except Exception:
        logger.exception("[%s] Failed to apply site config overrides", component)
        raise

    # Cloudflare bypass is optional; cookie resolver is required.
    try:
        from infrastructure.site_catalog.cloudflare_bypass import get_default_client

        set_cloudflare_bypass_client(get_default_client())
    except Exception as exc:
        logger.warning("[%s] Failed to configure Cloudflare bypass client: %s", component, exc)
    try:
        set_cookie_file_resolver(resolve_cookie_file_for_url)
        set_cookie_domain_resolver(resolve_cookie_match_domain_for_url)
    except Exception:
        logger.exception("[%s] Failed to configure cookie resolver", component)
        raise

    try:
        from infrastructure.site_catalog.youtube_oauth import get_oauth_credentials_for_daemon

        oauth_file = get_oauth_credentials_for_daemon()
        if oauth_file:
            os.environ["YOUTUBE_OAUTH_STATE_FILE"] = oauth_file
        get_site_plugin_registry().start_all()
    except Exception:
        logger.exception("[%s] Site plugin bootstrap failed", component)
        raise

    try:
        yield
    finally:
        try:
            get_site_plugin_registry().stop_all()
        except Exception:
            logger.warning("[%s] Site plugin shutdown failed", component, exc_info=True)


def create_shutdown_event(component: str) -> threading.Event:
    """Register signal handlers and return an Event that flips when shutdown is requested."""
    event = threading.Event()

    def _handle(sig, _frame):
        logger.info("[%s] Received signal %s, shutting down...", component, sig)
        event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle)

    return event


def wait_for_shutdown(event: threading.Event):
    """Block until shutdown_event is set."""
    try:
        while not event.is_set():
            event.wait(timeout=1.0)
    except KeyboardInterrupt:
        event.set()
