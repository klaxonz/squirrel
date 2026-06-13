import logging
import time

from workers.messaging.worker import worker_start, worker_stop
from application.lifespan import bootstrap_runtime, create_shutdown_event
from shared_kernel.system.config import SystemConfigService
from shared_kernel.system.constants import SYS_ENABLE_WORKER

logger = logging.getLogger(__name__)


def main():
    config_svc = SystemConfigService()
    shutdown_event = create_shutdown_event('worker')

    with bootstrap_runtime('worker'):
        is_running = False

        while not shutdown_event.is_set():
            enabled = config_svc.get_bool(SYS_ENABLE_WORKER, default=True)

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
