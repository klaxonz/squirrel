import logging
from threading import Lock
from typing import Optional
from schedule.schedule import Scheduler
from schedule.task import TaskRegistry, BaseTask
from utils import module_discovery

logger = logging.getLogger()

# module-scope state
_scheduler: Optional[Scheduler] = None
_scheduler_running: bool = False
_scheduler_lock = Lock()


def scheduler_start() -> None:
    module_discovery.import_classes_from_package("schedule.tasks", base_class=BaseTask)

    global _scheduler, _scheduler_running
    with _scheduler_lock:
        if _scheduler_running:
            logger.info("[scheduler] already running, skip start()")
            return

        logger.info("[scheduler] starting...")
        scheduler = Scheduler()
        for task_cls in TaskRegistry.tasks:
            logger.info(
                "[scheduler] register task %s interval=%s unit=%s start_immediately=%s",
                task_cls.__name__, task_cls.interval, task_cls.unit, task_cls.start_immediately,
            )
            scheduler.add_job(
                task_cls.run,
                interval=task_cls.interval,
                unit=task_cls.unit,
                start_immediately=task_cls.start_immediately,
            )
        scheduler.start()
        _scheduler = scheduler
        _scheduler_running = True
        logger.info("[scheduler] started")


def scheduler_stop() -> None:
    global _scheduler, _scheduler_running
    with _scheduler_lock:
        if not _scheduler_running:
            logger.info("[scheduler] not running, skip stop()")
            return
        logger.info("[scheduler] stopping...")
        try:
            if _scheduler:
                _scheduler.stop()

        finally:
            _scheduler = None
            _scheduler_running = False
            logger.info("[scheduler] stopped")


def scheduler_status() -> dict:
    return {"running": _scheduler_running}