import logging
import threading
from collections.abc import Callable

from infrastructure.cache.redis_client import create_redis_client

logger = logging.getLogger(__name__)

_listener_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None


def _listen_for_reload_signals(component: str, reloader: Callable[[], None]):
    global _stop_event
    _stop_event = threading.Event()
    pubsub = None

    try:
        client = create_redis_client()
        pubsub = client.pubsub()
        pubsub.subscribe("squirrel:site-runtime:reload")
        logger.info("[%s] subscribed to site runtime reload channel", component)

        for message in pubsub.listen():
            if _stop_event.is_set():
                break

            if message["type"] == "message":
                logger.info("[%s] received site runtime reload signal", component)
                try:
                    reloader()
                    logger.info("[%s] site runtime reloaded successfully", component)
                except Exception as e:
                    # background thread safety net -- prevent a single reload failure from crashing the listener
                    logger.error("[%s] failed to reload site runtime: %s", component, e, exc_info=True)
    except (ConnectionError, OSError, ValueError) as e:
        logger.error("[%s] site runtime reload listener error: %s", component, e, exc_info=True)
    finally:
        if pubsub is not None:
            try:
                pubsub.close()
            except (AttributeError, ConnectionError, OSError):
                pass


def start_reload_listener(component: str, *, reloader: Callable[[], None]):
    """Start the reload listener thread.

    ``reloader`` is invoked on every received reload message; composition roots
    pass ``manager.reload_enabled_site_runtimes`` (or a lambda wrapping it).
    """
    global _listener_thread
    if _listener_thread is not None and _listener_thread.is_alive():
        logger.warning("[%s] reload listener already running", component)
        return

    _listener_thread = threading.Thread(
        target=_listen_for_reload_signals,
        args=(component, reloader),
        daemon=True,
        name=f"site-runtime-reload-listener-{component}",
    )
    _listener_thread.start()
    logger.info("[%s] started site runtime reload listener", component)


def stop_reload_listener(component: str):
    global _stop_event, _listener_thread
    if _stop_event is not None:
        _stop_event.set()
        logger.info("[%s] stopping site runtime reload listener", component)
    if _listener_thread is not None:
        _listener_thread.join(timeout=5)
        _listener_thread = None
