import logging
from datetime import datetime
from threading import Lock, Thread

from infrastructure.database.session import get_session
from infrastructure.scheduling.bootstrap import ensure_system_tasks
from infrastructure.scheduling.engine import Scheduler
from infrastructure.scheduling.models.scheduler_status import SchedulerStatus
from infrastructure.scheduling.store import dynamic_task_manager
from infrastructure.scheduling.sync import SchedulerTaskSynchronizer

logger = logging.getLogger(__name__)

# module-scope state
_scheduler: Scheduler | None = None
_scheduler_running: bool = False
_scheduler_lock = Lock()
_heartbeat_thread: Thread | None = None
_heartbeat_running: bool = False
_task_synchronizer = SchedulerTaskSynchronizer()


def _update_scheduler_status(is_running: bool, job_count: int = 0, error_message: str | None = None) -> None:
    """Update scheduler status in the database"""
    try:
        with get_session() as session:
            status = session.query(SchedulerStatus).filter(
                SchedulerStatus.process_name == "scheduler",
            ).first()

            if not status:
                status = SchedulerStatus(process_name="scheduler")
                session.add(status)

            status.is_running = is_running
            status.job_count = job_count
            status.last_heartbeat = datetime.now()

            if is_running and not status.started_at:
                status.started_at = datetime.now()
                status.stopped_at = None
            elif not is_running:
                status.stopped_at = datetime.now()

            if error_message:
                status.error_message = error_message

            session.commit()
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        logger.error("Failed to update scheduler status: %s", e)

def _heartbeat_worker() -> None:
    """Heartbeat thread that periodically updates scheduler status"""
    global _heartbeat_running, _scheduler
    import time

    while _heartbeat_running:
        try:
            job_count = 0
            if _scheduler and _scheduler_running:
                job_count = len(_scheduler.jobs) if hasattr(_scheduler, "jobs") else 0

            _update_scheduler_status(is_running=_scheduler_running, job_count=job_count)
            if _scheduler_running:
                _task_synchronizer.sync_scheduled_tasks()
                _task_synchronizer.consume_manual_triggers()
        except Exception as e:  # process boundary -- must not crash supervisor
            logger.error("Heartbeat error: %s", e, exc_info=True)

        time.sleep(5)


def scheduler_start() -> None:
    global _scheduler, _scheduler_running, _heartbeat_thread, _heartbeat_running
    with _scheduler_lock:
        if _scheduler_running:
            logger.info("[scheduler] already running, skip start()")
            return

        logger.info("[scheduler] starting...")
        scheduler = Scheduler()

        dynamic_task_manager.initialize(scheduler)
        ensure_system_tasks()
        _task_synchronizer.seed_task_fingerprints()

        dynamic_task_manager.load_and_register_tasks()

        scheduler.start()
        _scheduler = scheduler
        _scheduler_running = True

        job_count = len(scheduler.jobs) if hasattr(scheduler, "jobs") else 0

        _update_scheduler_status(is_running=True, job_count=job_count)

        _heartbeat_running = True
        _heartbeat_thread = Thread(target=_heartbeat_worker, daemon=True)
        _heartbeat_thread.start()

        logger.info("[scheduler] started with %s jobs", job_count)


def scheduler_stop() -> None:
    global _scheduler, _scheduler_running, _heartbeat_running, _heartbeat_thread
    with _scheduler_lock:
        if not _scheduler_running:
            logger.info("[scheduler] not running, skip stop()")
            return
        logger.info("[scheduler] stopping...")
        try:
            _heartbeat_running = False
            if _heartbeat_thread:
                _heartbeat_thread.join(timeout=2)

            if _scheduler:
                _scheduler.stop()

        finally:
            _scheduler = None
            _scheduler_running = False
            _heartbeat_thread = None
            _update_scheduler_status(is_running=False, job_count=0)
            logger.info("[scheduler] stopped")


def scheduler_status() -> dict:
    """Read scheduler status from the database (cross-process)"""
    try:
        with get_session() as session:
            status = session.query(SchedulerStatus).filter(
                SchedulerStatus.process_name == "scheduler",
            ).first()

            if not status:
                return {
                    "running": False,
                    "job_count": 0,
                    "last_heartbeat": None,
                    "started_at": None,
                }

            heartbeat_age = (datetime.now() - status.last_heartbeat).total_seconds()
            is_alive = status.is_running and heartbeat_age < 30

            return {
                "running": is_alive,
                "job_count": status.job_count,
                "last_heartbeat": status.last_heartbeat.isoformat() if status.last_heartbeat else None,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "heartbeat_age": heartbeat_age,
            }
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        logger.error("Failed to get scheduler status: %s", e)
        return {
            "running": False,
            "job_count": 0,
            "error": str(e),
        }
