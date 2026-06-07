import logging
from datetime import datetime
from threading import Lock, Thread

from core.database import get_session
from core.dynamic_task_manager import dynamic_task_manager
from models.scheduler_status import SchedulerStatus
from schedule.schedule import Scheduler
from services import outbox_event_service
from services.scheduled_task_bootstrap import ensure_system_tasks

logger = logging.getLogger(__name__)

# module-scope state
_scheduler: Scheduler | None = None
_scheduler_running: bool = False
_scheduler_lock = Lock()
_heartbeat_thread: Thread | None = None
_heartbeat_running: bool = False
_outbox_listener_thread: Thread | None = None
_outbox_listener_stop_event = None
_task_sync_lock = Lock()
_task_fingerprints: dict[int, tuple] = {}


def _update_scheduler_status(is_running: bool, job_count: int = 0, error_message: str = None) -> None:
    """更新调度器状态到数据库"""
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
        logger.error(f"Failed to update scheduler status: {e}")

def _get_task_fingerprint(task) -> tuple:
    return (
        bool(getattr(task, "is_active", False)),
        int(getattr(task, "interval", 0)),
        str(getattr(task, "unit", "")),
        bool(getattr(task, "start_immediately", False)),
    )


def _seed_task_fingerprints() -> None:
    from models.scheduled_task import ScheduledTask

    global _task_fingerprints
    with get_session() as session:
        tasks = session.query(ScheduledTask).all()
        _task_fingerprints = {task.id: _get_task_fingerprint(task) for task in tasks}


def _sync_scheduled_tasks() -> None:
    from models.scheduled_task import ScheduledTask

    global _task_fingerprints

    with _task_sync_lock, get_session() as session:
        tasks = session.query(ScheduledTask).all()
        current_ids = set()

        for task in tasks:
            current_ids.add(task.id)
            fingerprint = _get_task_fingerprint(task)
            prev_fingerprint = _task_fingerprints.get(task.id)

            if prev_fingerprint is None:
                if task.is_active:
                    dynamic_task_manager.add_task(task)
                _task_fingerprints[task.id] = fingerprint
                continue

            if fingerprint != prev_fingerprint:
                dynamic_task_manager.update_task(task)
                _task_fingerprints[task.id] = fingerprint

        removed_ids = set(_task_fingerprints.keys()) - current_ids
        for task_id in removed_ids:
            dynamic_task_manager.remove_task(task_id)
            del _task_fingerprints[task_id]

def _consume_manual_triggers() -> None:
    from models.scheduled_task import TaskExecutionLog

    pending: list[tuple[int, int, str]] = []
    with get_session() as session:
        logs = session.query(TaskExecutionLog).filter(
            TaskExecutionLog.status == "manual_trigger",
        ).order_by(TaskExecutionLog.started_at).limit(20).all()

        for log in logs:
            executed_by = log.executed_by or "manual"
            log.executed_by = executed_by
            log.status = "queued"
            pending.append((log.task_id, log.id, executed_by))

    for task_id, log_id, executed_by in pending:
        dynamic_task_manager.execute_task_now(task_id, execution_log_id=log_id, executed_by=executed_by)


def _heartbeat_worker() -> None:
    """心跳线程，定期更新调度器状态"""
    global _heartbeat_running, _scheduler
    import time

    while _heartbeat_running:
        try:
            job_count = 0
            if _scheduler and _scheduler_running:
                job_count = len(_scheduler.jobs) if hasattr(_scheduler, "jobs") else 0

            _update_scheduler_status(is_running=_scheduler_running, job_count=job_count)
            if _scheduler_running:
                _sync_scheduled_tasks()
                _consume_manual_triggers()
        except Exception as e:  # process boundary -- must not crash supervisor
            logger.error(f"Heartbeat error: {e}", exc_info=True)

        time.sleep(5)


def scheduler_start() -> None:
    global _scheduler, _scheduler_running, _heartbeat_thread, _heartbeat_running, _outbox_listener_thread, _outbox_listener_stop_event
    with _scheduler_lock:
        if _scheduler_running:
            logger.info("[scheduler] already running, skip start()")
            return

        logger.info("[scheduler] starting...")
        scheduler = Scheduler()

        dynamic_task_manager.initialize(scheduler)
        ensure_system_tasks()
        _seed_task_fingerprints()

        dynamic_task_manager.load_and_register_tasks()

        scheduler.start()
        _scheduler = scheduler
        _scheduler_running = True

        job_count = len(scheduler.jobs) if hasattr(scheduler, "jobs") else 0

        _update_scheduler_status(is_running=True, job_count=job_count)

        _heartbeat_running = True
        _heartbeat_thread = Thread(target=_heartbeat_worker, daemon=True)
        _heartbeat_thread.start()

        _outbox_listener_stop_event = outbox_event_service.create_listener_stop_event()
        _outbox_listener_thread = Thread(
            target=outbox_event_service.run_notification_listener,
            args=(_outbox_listener_stop_event,),
            daemon=True,
        )
        _outbox_listener_thread.start()

        logger.info(f"[scheduler] started with {job_count} jobs")


def scheduler_stop() -> None:
    global _scheduler, _scheduler_running, _heartbeat_running, _heartbeat_thread, _outbox_listener_thread, _outbox_listener_stop_event
    with _scheduler_lock:
        if not _scheduler_running:
            logger.info("[scheduler] not running, skip stop()")
            return
        logger.info("[scheduler] stopping...")
        try:
            _heartbeat_running = False
            if _heartbeat_thread:
                _heartbeat_thread.join(timeout=2)

            if _outbox_listener_stop_event is not None:
                _outbox_listener_stop_event.set()
            if _outbox_listener_thread:
                _outbox_listener_thread.join(timeout=2)

            if _scheduler:
                _scheduler.stop()

        finally:
            _scheduler = None
            _scheduler_running = False
            _heartbeat_thread = None
            _outbox_listener_thread = None
            _outbox_listener_stop_event = None
            _update_scheduler_status(is_running=False, job_count=0)
            logger.info("[scheduler] stopped")


def scheduler_status() -> dict:
    """从数据库读取调度器状态（支持跨进程）"""
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
        logger.error(f"Failed to get scheduler status: {e}")
        return {
            "running": False,
            "job_count": 0,
            "error": str(e),
        }
