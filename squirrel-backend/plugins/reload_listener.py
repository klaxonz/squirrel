import logging
import threading

from core.cache import create_redis_client
from plugins.manager import reload_plugin_runtime

logger = logging.getLogger(__name__)

_listener_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None


def _listen_for_reload_signals(component: str):
    global _stop_event
    _stop_event = threading.Event()

    try:
        client = create_redis_client()
        pubsub = client.pubsub()
        pubsub.subscribe("squirrel:plugin:reload")
        logger.info("[%s] subscribed to plugin reload channel", component)

        for message in pubsub.listen():
            if _stop_event.is_set():
                break

            if message["type"] == "message":
                logger.info("[%s] received plugin reload signal", component)
                try:
                    reload_plugin_runtime()
                    logger.info("[%s] plugin runtime reloaded successfully", component)
                except Exception as e:
                    logger.error("[%s] failed to reload plugin runtime: %s", component, e, exc_info=True)
    except Exception as e:
        logger.error("[%s] plugin reload listener error: %s", component, e, exc_info=True)
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


def start_reload_listener(component: str):
    global _listener_thread
    if _listener_thread is not None and _listener_thread.is_alive():
        logger.warning("[%s] reload listener already running", component)
        return

    _listener_thread = threading.Thread(
        target=_listen_for_reload_signals,
        args=(component,),
        daemon=True,
        name=f"plugin-reload-listener-{component}"
    )
    _listener_thread.start()
    logger.info("[%s] started plugin reload listener", component)


def stop_reload_listener(component: str):
    global _stop_event, _listener_thread
    if _stop_event is not None:
        _stop_event.set()
        logger.info("[%s] stopping plugin reload listener", component)
    if _listener_thread is not None:
        _listener_thread.join(timeout=5)
        _listener_thread = None
