import logging
import importlib
import inspect
from typing import Dict, Type, Any, Optional, Callable
from datetime import datetime, timedelta
from threading import Lock

from core.database import get_session
from models.scheduled_task import ScheduledTask, TaskStatus, TaskType, TaskExecutionLog
from schedule.task import BaseTask
from utils import module_discovery

logger = logging.getLogger(__name__)


class TaskFactory:
    """任务工厂类，负责动态创建任务实例"""

    def __init__(self):
        self._task_classes: Dict[str, Type[BaseTask]] = {}
        self._lock = Lock()

    def discover_builtin_tasks(self) -> None:
        """发现并注册内置任务"""
        try:
            # 发现所有继承BaseTask的类
            task_classes = module_discovery.import_classes_from_package(
                "schedule.tasks", base_class=BaseTask
            )

            with self._lock:
                for task_class in task_classes:
                    task_name = f"{task_class.__module__}.{task_class.__name__}"
                    self._task_classes[task_name] = task_class
                    logger.info(f"Discovered builtin task: {task_name}")
        except Exception as e:
            logger.error(f"Failed to discover builtin tasks: {e}")

    def register_task_class(self, task_class: Type[BaseTask], task_name: str = None) -> None:
        """注册任务类"""
        if task_name is None:
            task_name = f"{task_class.__module__}.{task_class.__name__}"

        with self._lock:
            self._task_classes[task_name] = task_class
            logger.info(f"Registered task class: {task_name}")

    def get_task_class(self, task_class_name: str) -> Optional[Type[BaseTask]]:
        """获取任务类"""
        with self._lock:
            return self._task_classes.get(task_class_name)

    def create_task_instance(self, task_config: ScheduledTask) -> Optional[BaseTask]:
        """根据配置创建任务实例"""
        task_class = self.get_task_class(task_config.task_class)
        if not task_class:
            logger.error(f"Task class not found: {task_config.task_class}")
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
        except Exception as e:
            logger.error(f"Failed to create task instance for {task_config.name}: {e}")
            return None

    def get_available_task_classes(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的任务类信息"""
        result = {}
        with self._lock:
            for task_name, task_class in self._task_classes.items():
                result[task_name] = {
                    'name': task_name,
                    'description': getattr(task_class, '__doc__', '').strip() or 'No description',
                    'module': task_class.__module__,
                    'class_name': task_class.__name__,
                    'default_interval': getattr(task_class, 'interval', 60),
                    'default_unit': getattr(task_class, 'unit', 'seconds'),
                    'default_start_immediately': getattr(task_class, 'start_immediately', True),
                }
        return result


class DynamicTaskManager:
    """动态任务管理器"""

    def __init__(self):
        self.task_factory = TaskFactory()
        self._scheduler = None
        self._active_tasks: Dict[int, Any] = {}  # task_id -> scheduler_job
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
                ScheduledTask.is_active == True,
                ScheduledTask.status == TaskStatus.ENABLED.value
            ).all()

            logger.info(f"Loading {len(active_tasks)} active tasks from database")

            for task_config in active_tasks:
                try:
                    self._register_task_to_scheduler(task_config)
                except Exception as e:
                    logger.error(f"Failed to register task {task_config.name}: {e}")
                    # 更新任务状态为错误
                    task_config.status = TaskStatus.ERROR.value
                    task_config.last_error = str(e)
                    session.commit()

    def _register_task_to_scheduler(self, task_config: ScheduledTask) -> None:
        """将任务注册到调度器"""
        task_instance = self.task_factory.create_task_instance(task_config)
        if not task_instance:
            raise ValueError(f"Cannot create task instance for {task_config.name}")

        # 创建包装函数，用于执行任务并记录日志
        def task_wrapper():
            self._execute_task_with_logging(task_config)

        # 注册到调度器
        scheduler_job = self._scheduler.add_job(
            func=task_wrapper,
            interval=task_config.interval,
            unit=task_config.unit,
            start_immediately=task_config.start_immediately,
            job_name=task_config.name
        )

        with self._lock:
            self._active_tasks[task_config.id] = scheduler_job

        # 更新下次执行时间
        self._update_next_run_time(task_config)

        logger.info(f"Registered task {task_config.name} to scheduler")

    def _execute_task_with_logging(self, task_config: ScheduledTask) -> None:
        """执行任务并记录日志"""
        start_time = datetime.now()
        execution_log = None

        try:
            # 创建执行日志记录
            with get_session() as session:
                execution_log = TaskExecutionLog(
                    task_id=task_config.id,
                    task_name=task_config.name,
                    started_at=start_time,
                    status='running',
                    executed_by='system'
                )
                session.add(execution_log)
                session.commit()

            # 执行任务
            task_instance = self.task_factory.create_task_instance(task_config)
            if task_instance:
                result = task_instance.run()

                # 更新执行成功状态
                end_time = datetime.now()
                duration = int((end_time - start_time).total_seconds() * 1000)

                with get_session() as session:
                    task_config.last_run_at = start_time
                    task_config.run_count += 1
                    task_config.success_count += 1
                    task_config.status = TaskStatus.ENABLED.value
                    task_config.last_error = None
                    session.commit()

                    if execution_log:
                        execution_log.finished_at = end_time
                        execution_log.duration = duration
                        execution_log.status = 'success'
                        execution_log.result_data = result if result else {}
                        session.commit()

                logger.info(f"Task {task_config.name} executed successfully in {duration}ms")
            else:
                raise ValueError("Cannot create task instance")

        except Exception as e:
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() * 1000)
            error_msg = str(e)

            # 更新执行失败状态
            with get_session() as session:
                task_config.last_run_at = start_time
                task_config.run_count += 1
                task_config.error_count += 1
                task_config.status = TaskStatus.ERROR.value
                task_config.last_error = error_msg
                session.commit()

                if execution_log:
                    execution_log.finished_at = end_time
                    execution_log.duration = duration
                    execution_log.status = 'error'
                    execution_log.error_message = error_msg
                    session.commit()

            logger.error(f"Task {task_config.name} execution failed: {error_msg}")

        finally:
            # 更新下次执行时间
            self._update_next_run_time(task_config)

    def _update_next_run_time(self, task_config: ScheduledTask) -> None:
        """更新任务的下次执行时间"""
        try:
            # 计算下次执行时间
            multipliers = {
                'seconds': 1,
                'minutes': 60,
                'hours': 3600,
                'days': 86400
            }
            interval_seconds = task_config.interval * multipliers.get(task_config.unit, 1)
            next_run = datetime.now() + timedelta(seconds=interval_seconds)

            with get_session() as session:
                task_config.next_run_at = next_run
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update next run time for {task_config.name}: {e}")

    def add_task(self, task_config: ScheduledTask) -> bool:
        """添加新任务"""
        try:
            if task_config.is_active and task_config.status == TaskStatus.ENABLED.value:
                self._register_task_to_scheduler(task_config)
            return True
        except Exception as e:
            logger.error(f"Failed to add task {task_config.name}: {e}")
            return False

    def remove_task(self, task_id: int) -> bool:
        """移除任务"""
        try:
            with self._lock:
                if task_id in self._active_tasks:
                    # 从调度器中移除任务
                    job = self._active_tasks[task_id]
                    if hasattr(self._scheduler, 'remove_job'):
                        self._scheduler.remove_job(job)
                    del self._active_tasks[task_id]
            return True
        except Exception as e:
            logger.error(f"Failed to remove task {task_id}: {e}")
            return False

    def update_task(self, task_config: ScheduledTask) -> bool:
        """更新任务配置"""
        try:
            # 先移除旧任务
            self.remove_task(task_config.id)

            # 如果任务激活且启用，则重新注册
            if task_config.is_active and task_config.status == TaskStatus.ENABLED.value:
                self._register_task_to_scheduler(task_config)
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_config.name}: {e}")
            return False

    def execute_task_now(self, task_id: int) -> bool:
        """立即执行任务"""
        try:
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return False

                # 在新线程中执行任务
                from threading import Thread
                thread = Thread(target=self._execute_task_with_logging, args=(task_config,))
                thread.daemon = True
                thread.start()

                return True
        except Exception as e:
            logger.error(f"Failed to execute task {task_id} now: {e}")
            return False


# 全局任务管理器实例
dynamic_task_manager = DynamicTaskManager()
