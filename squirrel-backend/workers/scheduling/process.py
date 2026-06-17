import logging
import time

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
from domains.system.application.services.config_service import SystemConfigService
from domains.system.domain.models.constants import SYS_ENABLE_SCHEDULER
from infrastructure.scheduling.lifecycle import scheduler_start, scheduler_stop
from workers.bootstrap import bootstrap_runtime, create_shutdown_event

logger = logging.getLogger(__name__)


def main():
    config_svc = SystemConfigService()
    shutdown_event = create_shutdown_event('scheduler')

    with bootstrap_runtime('scheduler'):
        # 清理上次 crash/interrupt 留下的脏 sync 状态（drained terminal / stale queued / expired running）。
        # 只在 scheduler 进程启动时做——它才是推进 subscription sync 的进程。
        try:
            recovered = subscription_sync_state_service.recover_stale_sync_states_on_startup()
            if any(recovered.values()):
                logger.info(
                    "[scheduler] Recovered stale sync states on startup: %s", recovered,
                )
        except Exception:
            logger.warning("[scheduler] Failed to recover stale sync states", exc_info=True)

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
