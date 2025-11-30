import logging

from controllers.worker_controller import worker_start, worker_stop
from processes.service_runtime import bootstrap_runtime, create_shutdown_event, wait_for_shutdown


logger = logging.getLogger(__name__)


def main():
    shutdown_event = create_shutdown_event("worker")

    with bootstrap_runtime("worker"):
        logger.info("[worker] Starting worker threads...")
        worker_start()
        try:
            wait_for_shutdown(shutdown_event)
        finally:
            logger.info("[worker] Stopping worker threads...")
            worker_stop()

    logger.info("[worker] Worker process exited")


if __name__ == "__main__":
    main()
