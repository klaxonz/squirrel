import logging
import time

from common.constants import SYS_ENABLE_WORKER
from processes.managers.worker_manager import worker_start, worker_stop
from processes.service_runtime import bootstrap_runtime, create_shutdown_event
from services import system_config_service


logger = logging.getLogger(__name__)


def main():
    shutdown_event = create_shutdown_event("worker")

    with bootstrap_runtime("worker"):
        is_running = False

        while not shutdown_event.is_set():
            enabled = system_config_service.get_bool(SYS_ENABLE_WORKER, default=True)

            if enabled and not is_running:
                logger.info("[worker] Starting worker threads...")
                worker_start()
                is_running = True
            elif not enabled and is_running:
                logger.info("[worker] Stopping worker threads...")
                worker_stop()
                is_running = False

            time.sleep(5)

        if is_running:
            logger.info("[worker] Stopping worker threads before exit...")
            worker_stop()

    logger.info("[worker] Worker process exited")


if __name__ == "__main__":
    main()
