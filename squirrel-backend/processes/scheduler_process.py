import logging
import time

from common.constants import SYS_ENABLE_SCHEDULER
from processes.managers.scheduler_manager import scheduler_start, scheduler_stop
from processes.service_runtime import bootstrap_runtime, create_shutdown_event
from services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)


def main():
    config_svc = SystemConfigService()
    shutdown_event = create_shutdown_event('scheduler')

    with bootstrap_runtime('scheduler'):
        is_running = False

        while not shutdown_event.is_set():
            enabled = config_svc.get_bool(SYS_ENABLE_SCHEDULER, default=True)

            if enabled and not is_running:
                logger.info("[scheduler] Starting scheduler...")
                scheduler_start()
                is_running = True
            elif not enabled and is_running:
                logger.info("[scheduler] Stopping scheduler...")
                scheduler_stop()
                is_running = False

            time.sleep(5)

        if is_running:
            logger.info("[scheduler] Stopping scheduler before exit...")
            scheduler_stop()

    logger.info("[scheduler] Scheduler process exited")


if __name__ == "__main__":
    main()
