import logging

from controllers.scheduler_controller import scheduler_start, scheduler_stop
from processes.service_runtime import bootstrap_runtime, create_shutdown_event, wait_for_shutdown


logger = logging.getLogger(__name__)


def main():
    shutdown_event = create_shutdown_event("scheduler")

    with bootstrap_runtime("scheduler"):
        logger.info("[scheduler] Starting scheduler...")
        scheduler_start()
        try:
            wait_for_shutdown(shutdown_event)
        finally:
            logger.info("[scheduler] Stopping scheduler...")
            scheduler_stop()

    logger.info("[scheduler] Scheduler process exited")


if __name__ == "__main__":
    main()
