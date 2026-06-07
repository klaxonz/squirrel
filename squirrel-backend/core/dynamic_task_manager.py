import logging
from datetime import datetime
from threading import Lock
from typing import Any

from core.database import get_session
from models.scheduled_task import ScheduledTask, TaskExecutionLog, TaskStatus
from schedule.task import BaseTask
from utils import module_discovery

logger = logging.getLogger(__name__)


class TaskFactory:
    """任务工厂类，负责动态创建任务实例"""

    def __init__(self):
        self._task_classes: dict[str, type[BaseTask]] = {}
        self._lock = Lock()

    def discover_builtin_tasks(self) -> None:
        """发现并注册内置任务"""
        try:
            # 发现所有继承BaseTask的类
            task_classes = module_discovery.import_classes_from_package(
                "schedule.tasks", base_class=BaseTask,
            )

            with self._lock:
                for task_class in task_classes:
                    task_name = f"{task_class.__module__}.{task_class.__name__}"
                    self._task_classes[task_name] = task_class
                    logger.info("Discovered builtin task: %s", task_name)
        except ImportError as e:
            logger.error("Failed to discover builtin tasks: %s", e)

    def register_task_class(self, task_class: type[BaseTask], task_name: str = None) -> None:
        """注册任务类"""
        if task_name is None:
            task_name = f"{task_class.__module__}.{task_class.__name__}"

        with self._lock:
            self._task_classes[task_name] = task_class
            logger.info("Registered task class: %s", task_name)

    def get_task_class(self, task_class_name: str) -> type[BaseTask] | None:
        """获取任务类"""
        with self._lock:
            return self._task_classes.get(task_class_name)

    def create_task_instance(self, task_config: ScheduledTask) -> BaseTask | None:
        """根据配置创建任务实例"""
        task_class = self.get_task_class(task_config.task_class)
        if not task_class:
            logger.error("Task class not found: %s", task_config.task_class)
            return None

        try:
            # 创建任务实例并设置配置
            task_instance = task_class()
            task_instance.interval = task_config.interval
            task_instance.unit = task_config.unit
            task_instance.start_immediately = task_config.start_immediately

            # 如果有任务参数，可以在这里设置
            if task_config.task_params:
                for key, value in task_config.task_params.items():
                    if hasattr(task_instance, key):
                        setattr(task_instance, key, value)

            return task_instance
        except (TypeError, ValueError, AttributeError) as e:
            logger.error("Failed to create task instance for %s: %s", task_config.name, e)
            return None

    def get_available_task_classes(self) -> dict[str, dict[str, Any]]:
        """获取所有可用的任务类信息"""
        result = {}
        with self._lock:
            for task_name, task_class in self._task_classes.items():
                result[task_name] = {
                    "name": task_name,
                    "description": (getattr(task_class, "__doc__", "") or "").strip() or "No description",
                    "module": task_class.__module__,
                    "class_name": task_class.__name__,
                    "default_interval": getattr(task_class, "interval", 60),
                    "default_unit": getattr(task_class, "unit", "seconds"),
                    "default_start_immediately": getattr(task_class, "start_immediately", True),
                }
        return result


class DynamicTaskManager:
    """动态任务管理器"""

    def __init__(self):
        self.task_factory = TaskFactory()
        self._scheduler = None
        self._active_tasks: dict[int, Any] = {}  # task_id -> scheduler_job
        self._lock = Lock()

    def initialize(self, scheduler_instance):
        """初始化任务管理器"""
        self._scheduler = scheduler_instance
        self.task_factory.discover_builtin_tasks()
        logger.info("DynamicTaskManager initialized")

    def load_and_register_tasks(self) -> None:
        """从数据库加载并注册所有活跃任务"""
        if not self._scheduler:
            logger.error("Scheduler not initialized")
            return

        with get_session() as session:
            # 获取所有活跃任务
            active_tasks = session.query(ScheduledTask).filter(
                ScheduledTask.is_active,
            ).all()

            logger.info("Loading %s active tasks from database", len(active_tasks))

            for task_config in active_tasks:
                try:
                    self._register_task_to_scheduler(task_config)
                except (ValueError, TypeError, AttributeError, KeyError) as e:
                    logger.error("Failed to register task %s: %s", task_config.name, e)
                    # 更新任务状态为错误
                    task_config.status = TaskStatus.ERROR.value
                    task_config.last_error = str(e)
                    session.commit()

    def _register_task_to_scheduler(self, task_config: ScheduledTask) -> None:
        """将任务注册到调度器"""
        if not self._scheduler:
            raise ValueError("Scheduler not initialized")

        task_instance = self.task_factory.create_task_instance(task_config)
        if not task_instance:
            raise ValueError(f"Cannot create task instance for {task_config.name}")

        task_id = task_config.id
        job_ref: dict[str, Any] = {}

        def task_wrapper():
            job = job_ref.get("job")
            next_run_at = None
            if job and isinstance(job.get("next_run"), (int, float)):
                next_run_at = datetime.fromtimestamp(job["next_run"])
            self._execute_task_with_logging(task_id, next_run_at=next_run_at)

        scheduler_job = self._scheduler.add_job(
            func=task_wrapper,
            interval=task_config.interval,
            unit=task_config.unit,
            start_immediately=task_config.start_immediately,
            job_name=task_config.name,
        )
        job_ref["job"] = scheduler_job

        with self._lock:
            self._active_tasks[task_id] = scheduler_job

        if scheduler_job and isinstance(scheduler_job.get("next_run"), (int, float)):
            self._update_next_run_time(task_id, datetime.fromtimestamp(scheduler_job["next_run"]))

        logger.info("Registered task %s to scheduler", task_config.name)

    def _execute_task_with_logging(
        self,
        task_id: int,
        next_run_at: datetime | None = None,
        execution_log_id: int | None = None,
        executed_by: str = "system",
    ) -> None:
        """执行任务并记录日志"""
        start_time = datetime.now()
        task_snapshot: ScheduledTask | None = None

        try:
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    logger.error("Task not found: %s", task_id)
                    return

                task_snapshot = task_config

                if execution_log_id is not None:
                    existing_log = session.query(TaskExecutionLog).filter(TaskExecutionLog.id == execution_log_id).first()
                    if not existing_log or existing_log.task_id != task_id:
                        execution_log_id = None
                    else:
                        existing_log.started_at = start_time
                        existing_log.status = "running"
                        existing_log.executed_by = executed_by
                        task_config.status = TaskStatus.RUNNING.value
                        session.flush()

                if execution_log_id is None:
                    execution_log = TaskExecutionLog(
                        task_id=task_id,
                        task_name=task_config.name,
                        started_at=start_time,
                        status="running",
                        executed_by=executed_by,
                    )
                    session.add(execution_log)
                    task_config.status = TaskStatus.RUNNING.value
                    session.flush()
                    execution_log_id = execution_log.id

            task_instance = self.task_factory.create_task_instance(task_snapshot)
            if not task_instance:
                raise ValueError("Cannot create task instance")

            result = task_instance.run()

            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() * 1000)

            with get_session() as session:
                persisted_task = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if persisted_task:
                    persisted_task.last_run_at = start_time
                    persisted_task.run_count += 1
                    persisted_task.success_count += 1
                    persisted_task.status = TaskStatus.ENABLED.value
                    persisted_task.last_error = None
                    if next_run_at:
                        persisted_task.next_run_at = next_run_at

                if execution_log_id:
                    persisted_log = session.query(TaskExecutionLog).filter(TaskExecutionLog.id == execution_log_id).first()
                    if persisted_log:
                        persisted_log.finished_at = end_time
                        persisted_log.duration = duration
                        persisted_log.status = "success"
                        persisted_log.result_data = result or {}
                        persisted_log.error_message = None

            task_name = task_snapshot.name if task_snapshot else str(task_id)
            logger.info("Task %s executed successfully in %sms", task_name, duration)

        except Exception as e:  # task execution boundary — persist error state and continue
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() * 1000)
            error_msg = str(e)

            with get_session() as session:
                persisted_task = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if persisted_task:
                    persisted_task.last_run_at = start_time
                    persisted_task.run_count += 1
                    persisted_task.error_count += 1
                    persisted_task.status = TaskStatus.ERROR.value
                    persisted_task.last_error = error_msg
                    if next_run_at:
                        persisted_task.next_run_at = next_run_at

                if execution_log_id:
                    persisted_log = session.query(TaskExecutionLog).filter(TaskExecutionLog.id == execution_log_id).first()
                    if persisted_log:
                        persisted_log.finished_at = end_time
                        persisted_log.duration = duration
                        persisted_log.status = "error"
                        persisted_log.error_message = error_msg
                        persisted_log.result_data = None

            task_name = task_snapshot.name if task_snapshot else str(task_id)
            logger.error("Task %s execution failed: %s", task_name, error_msg)

    def _update_next_run_time(self, task_id: int, next_run_at: datetime) -> None:
        """更新任务的下次执行时间"""
        try:
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return
                task_config.next_run_at = next_run_at
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to update next run time for task %s: %s", task_id, e)

    def add_task(self, task_config: ScheduledTask) -> bool:
        """添加新任务"""
        try:
            if task_config.is_active:
                self._register_task_to_scheduler(task_config)
            return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Failed to add task %s: %s", task_config.name, e)
            return False

    def remove_task(self, task_id: int) -> bool:
        """移除任务"""
        try:
            with self._lock:
                if task_id in self._active_tasks:
                    # 从调度器中移除任务
                    job = self._active_tasks[task_id]
                    if hasattr(self._scheduler, "remove_job"):
                        self._scheduler.remove_job(job)
                    del self._active_tasks[task_id]
            return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Failed to remove task %s: %s", task_id, e)
            return False

    def update_task(self, task_config: ScheduledTask) -> bool:
        """更新任务配置"""
        try:
            # 先移除旧任务
            self.remove_task(task_config.id)

            # 如果任务激活且启用，则重新注册
            if task_config.is_active:
                self._register_task_to_scheduler(task_config)
            return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Failed to update task %s: %s", task_config.name, e)
            return False

    def execute_task_now(self, task_id: int, execution_log_id: int | None = None, executed_by: str = "system") -> bool:
        """立即执行任务"""
        try:
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return False

                # 在新线程中执行任务
                from threading import Thread
                thread = Thread(
                    target=self._execute_task_with_logging,
                    kwargs={
                        "task_id": task_id,
                        "execution_log_id": execution_log_id,
                        "executed_by": executed_by,
                    },
                )
                thread.daemon = True
                thread.start()

                return True
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to execute task %s now: %s", task_id, e)
            return False


# 全局任务管理器实例
dynamic_task_manager = DynamicTaskManager()
