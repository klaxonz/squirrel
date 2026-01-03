import logging
from threading import Lock, Thread
from typing import Optional, Dict, Any
from datetime import datetime
from schedule.schedule import Scheduler
from schedule.task import TaskRegistry, BaseTask
from utils import module_discovery
from core.dynamic_task_manager import dynamic_task_manager
from core.database import get_session
from models.scheduler_status import SchedulerStatus

logger = logging.getLogger()

# module-scope state
_scheduler: Optional[Scheduler] = None
_scheduler_running: bool = False
_scheduler_lock = Lock()
_heartbeat_thread: Optional[Thread] = None
_heartbeat_running: bool = False
_legacy_status_lock = Lock()


def _update_scheduler_status(is_running: bool, job_count: int = 0, error_message: str = None, legacy_tasks: dict = None) -> None:
    """更新调度器状态到数据库"""
    try:
        with get_session() as session:
            status = session.query(SchedulerStatus).filter(
                SchedulerStatus.process_name == 'scheduler'
            ).first()

            if not status:
                status = SchedulerStatus(process_name='scheduler')
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

            if legacy_tasks is not None:
                status.legacy_tasks = legacy_tasks

            session.commit()
    except Exception as e:
        logger.error(f"Failed to update scheduler status: {e}")

def _set_legacy_task_status(task_name: str, status: str, next_run_at: Optional[str] = None) -> None:
    try:
        with _legacy_status_lock:
            with get_session() as session:
                scheduler_status = session.query(SchedulerStatus).filter(
                    SchedulerStatus.process_name == 'scheduler'
                ).first()
                if not scheduler_status:
                    scheduler_status = SchedulerStatus(process_name='scheduler')
                    session.add(scheduler_status)

                legacy_tasks = dict(scheduler_status.legacy_tasks or {})
                task_info = dict(legacy_tasks.get(task_name) or {})
                task_info["status"] = status
                if next_run_at is not None:
                    task_info["next_run_at"] = next_run_at
                legacy_tasks[task_name] = task_info
                scheduler_status.legacy_tasks = legacy_tasks
    except Exception as e:
        logger.error(f"Failed to update legacy task status: {task_name}, error: {e}")


def _record_legacy_task_result(
    task_name: str,
    started_at: datetime,
    success: bool,
    next_run_at: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    try:
        with _legacy_status_lock:
            with get_session() as session:
                scheduler_status = session.query(SchedulerStatus).filter(
                    SchedulerStatus.process_name == 'scheduler'
                ).first()
                if not scheduler_status:
                    scheduler_status = SchedulerStatus(process_name='scheduler')
                    session.add(scheduler_status)

                legacy_tasks = dict(scheduler_status.legacy_tasks or {})
                task_info = dict(legacy_tasks.get(task_name) or {})

                task_info["last_run_at"] = started_at.isoformat()
                if next_run_at is not None:
                    task_info["next_run_at"] = next_run_at

                task_info["run_count"] = int(task_info.get("run_count", 0)) + 1

                if success:
                    task_info["success_count"] = int(task_info.get("success_count", 0)) + 1
                    task_info["last_error"] = None
                    task_info["status"] = "enabled"
                else:
                    task_info["error_count"] = int(task_info.get("error_count", 0)) + 1
                    task_info["last_error"] = error_message
                    task_info["status"] = "error"

                legacy_tasks[task_name] = task_info
                scheduler_status.legacy_tasks = legacy_tasks
    except Exception as e:
        logger.error(f"Failed to record legacy task result: {task_name}, error: {e}")


def _heartbeat_worker() -> None:
    """心跳线程，定期更新调度器状态"""
    global _heartbeat_running, _scheduler
    import time

    while _heartbeat_running:
        try:
            job_count = 0
            if _scheduler and _scheduler_running:
                job_count = len(_scheduler.jobs) if hasattr(_scheduler, 'jobs') else 0

            _update_scheduler_status(is_running=_scheduler_running, job_count=job_count)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

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

        module_discovery.import_classes_from_package("schedule.tasks", base_class=BaseTask)

        legacy_tasks_info: Dict[str, Any] = {}
        for task_cls in TaskRegistry.tasks:
            task_name = task_cls.__name__
            logger.info(
                "[scheduler] register legacy task %s interval=%s unit=%s start_immediately=%s",
                task_cls.__name__, task_cls.interval, task_cls.unit, task_cls.start_immediately,
            )

            job_ref: Dict[str, Any] = {}

            def legacy_wrapper(task_cls=task_cls, task_name=task_name, job_ref=job_ref):
                started_at = datetime.now()
                job = job_ref.get("job")
                next_run_at = None
                if job and isinstance(job.get("next_run"), (int, float)):
                    next_run_at = datetime.fromtimestamp(job["next_run"]).isoformat()

                _set_legacy_task_status(task_name, "running", next_run_at)

                try:
                    task_cls.run()
                except Exception as e:
                    _record_legacy_task_result(
                        task_name=task_name,
                        started_at=started_at,
                        success=False,
                        next_run_at=next_run_at,
                        error_message=str(e),
                    )
                    raise
                else:
                    _record_legacy_task_result(
                        task_name=task_name,
                        started_at=started_at,
                        success=True,
                        next_run_at=next_run_at,
                    )

            scheduler_job = scheduler.add_job(
                legacy_wrapper,
                interval=task_cls.interval,
                unit=task_cls.unit,
                start_immediately=task_cls.start_immediately,
                job_name=task_name,
            )
            job_ref["job"] = scheduler_job

            legacy_tasks_info[task_name] = {
                'name': task_name,
                'task_class': f'{task_cls.__module__}.{task_cls.__name__}',
                'description': (task_cls.__doc__ or '').strip(),
                'interval': task_cls.interval,
                'unit': task_cls.unit,
                'start_immediately': task_cls.start_immediately,
                'status': 'enabled',
                'last_run_at': None,
                'next_run_at': datetime.fromtimestamp(scheduler_job["next_run"]).isoformat()
                if scheduler_job and isinstance(scheduler_job.get("next_run"), (int, float))
                else None,
                'last_error': None,
                'run_count': 0,
                'success_count': 0,
                'error_count': 0,
            }

        dynamic_task_manager.load_and_register_tasks()

        scheduler.start()
        _scheduler = scheduler
        _scheduler_running = True

        job_count = len(scheduler.jobs) if hasattr(scheduler, 'jobs') else 0

        _update_scheduler_status(is_running=True, job_count=job_count, legacy_tasks=legacy_tasks_info)

        _heartbeat_running = True
        _heartbeat_thread = Thread(target=_heartbeat_worker, daemon=True)
        _heartbeat_thread.start()

        logger.info(f"[scheduler] started with {job_count} jobs ({len(legacy_tasks_info)} legacy tasks)")


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
    """从数据库读取调度器状态（支持跨进程）"""
    try:
        with get_session() as session:
            status = session.query(SchedulerStatus).filter(
                SchedulerStatus.process_name == 'scheduler'
            ).first()

            if not status:
                return {
                    "running": False,
                    "job_count": 0,
                    "last_heartbeat": None,
                    "started_at": None
                }

            heartbeat_age = (datetime.now() - status.last_heartbeat).total_seconds()
            is_alive = status.is_running and heartbeat_age < 30

            return {
                "running": is_alive,
                "job_count": status.job_count,
                "last_heartbeat": status.last_heartbeat.isoformat() if status.last_heartbeat else None,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "heartbeat_age": heartbeat_age
            }
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        return {
            "running": False,
            "job_count": 0,
            "error": str(e)
        }
