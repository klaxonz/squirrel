import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, func, or_

from infrastructure.database.session import get_session
from infrastructure.scheduling.bootstrap import discover_task_classes, ensure_system_tasks
from infrastructure.scheduling.models.scheduled_task import ScheduledTask, TaskExecutionLog, TaskStatus, TaskType
from infrastructure.scheduling.store import dynamic_task_manager
from infrastructure.search.query import escape_ilike

logger = logging.getLogger(__name__)


class ScheduledTaskService:
    """Scheduled task service"""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session

    def get_task_list(
        self,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> dict[str, Any]:
        """Get task list"""
        ensure_system_tasks()

        with self.session_factory() as session:
            db_tasks = session.query(ScheduledTask)

            if search:
                db_tasks = db_tasks.filter(
                    or_(
                        ScheduledTask.name.ilike(f'%{escape_ilike(search)}%'),
                        ScheduledTask.description.ilike(f'%{escape_ilike(search)}%'),
                    ),
                )

            if status:
                db_tasks = db_tasks.filter(ScheduledTask.status == status)

            if task_type:
                db_tasks = db_tasks.filter(ScheduledTask.task_type == task_type)

            total = db_tasks.with_entities(func.count(ScheduledTask.id)).scalar() or 0
            paginated_tasks = [
                task.to_dict()
                for task in db_tasks.order_by(desc(ScheduledTask.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            ]

        return {
            'page': page,
            'page_size': page_size,
            'total': total,
            'data': paginated_tasks,
        }

    @staticmethod
    def create_task(
        name: str,
        task_class: str,
        task_type: str = TaskType.USER.value,
        description: str | None = None,
        interval: int = 60,
        unit: str = 'seconds',
        start_immediately: bool = True,
        max_retries: int = 3,
        task_params: dict[str, Any] | None = None,
        is_active: bool = True,
        created_by: str | None = None,
    ) -> ScheduledTask | None:
        """Create a new task"""
        try:
            discover_task_classes()
            # 验证任务类是否存在
            if not dynamic_task_manager.task_factory.get_task_class(task_class):
                raise ValueError(f"Task class '{task_class}' not found")

            task_config = ScheduledTask(
                name=name,
                task_type=task_type,
                description=description,
                interval=interval,
                unit=unit,
                start_immediately=start_immediately,
                max_retries=max_retries,
                status=TaskStatus.ENABLED.value if is_active else TaskStatus.DISABLED.value,
                is_active=is_active,
                task_class=task_class,
                task_params=task_params or {},
                created_by=created_by,
                updated_by=created_by,
            )

            with get_session() as session:
                session.add(task_config)
                session.commit()
                session.refresh(task_config)

                logger.info('Created scheduled task: %s (ID: %s)', name, task_config.id)
                return task_config

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error('Failed to create task %s: %s', name, e)
            return None

    @staticmethod
    def update_task(
        task_id: int,
        name: str | None = None,
        description: str | None = None,
        interval: int | None = None,
        unit: str | None = None,
        start_immediately: bool | None = None,
        max_retries: int | None = None,
        task_params: dict[str, Any] | None = None,
        is_active: bool | None = None,
        updated_by: str | None = None,
    ) -> bool:
        """Update task configuration"""
        try:
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return False

                # 更新字段
                if name is not None:
                    task_config.name = name
                if description is not None:
                    task_config.description = description
                if interval is not None:
                    task_config.interval = interval
                if unit is not None:
                    task_config.unit = unit
                if start_immediately is not None:
                    task_config.start_immediately = start_immediately
                if max_retries is not None:
                    task_config.max_retries = max_retries
                if task_params is not None:
                    task_config.task_params = task_params
                if is_active is not None:
                    task_config.is_active = is_active
                    task_config.status = TaskStatus.ENABLED.value if is_active else TaskStatus.DISABLED.value

                task_config.updated_by = updated_by
                task_config.updated_at = datetime.now()

                session.commit()

                logger.info('Updated scheduled task: %s (ID: %s)', task_config.name, task_id)
                return True

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error('Failed to update task %s: %s', task_id, e)
            return False

    @staticmethod
    def delete_task(task_id: int) -> bool:
        """Delete a task"""
        try:
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return False

                if task_config.task_type == TaskType.SYSTEM.value:
                    logger.warning('Refuse to delete system task: %s (ID: %s)', task_config.name, task_id)
                    return False

                # 删除任务记录
                session.delete(task_config)
                session.commit()

                logger.info('Deleted scheduled task: %s (ID: %s)', task_config.name, task_id)
                return True

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error('Failed to delete task %s: %s', task_id, e)
            return False

    @staticmethod
    def enable_task(task_id: int, updated_by: str | None = None) -> bool:
        """Enable a task"""
        return ScheduledTaskService.update_task(
            task_id=task_id,
            is_active=True,
            updated_by=updated_by,
        )

    @staticmethod
    def disable_task(task_id: int, updated_by: str | None = None) -> bool:
        """Disable a task"""
        return ScheduledTaskService.update_task(
            task_id=task_id,
            is_active=False,
            updated_by=updated_by,
        )

    @staticmethod
    def execute_task_now(task_id: int, executed_by: str | None = None) -> bool:
        """Execute a task immediately"""
        try:
            # 记录执行请求
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return False

                # 创建手动执行请求(由 scheduler 进程消费并执行)
                execution_log = TaskExecutionLog(
                    task_id=task_id,
                    task_name=task_config.name,
                    started_at=datetime.now(),
                    status='manual_trigger',
                    executed_by=executed_by or 'manual',
                )
                session.add(execution_log)
                session.commit()

            return True

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error('Failed to execute task %s now: %s', task_id, e)
            return False

    @staticmethod
    def get_available_task_classes() -> dict[str, Any]:
        """Get available task classes"""
        discover_task_classes()
        return dynamic_task_manager.task_factory.get_available_task_classes()

    @staticmethod
    def get_task_statistics() -> dict[str, Any]:
        """Get task statistics"""
        ensure_system_tasks()

        with get_session() as session:
            db_total_tasks = session.query(ScheduledTask).count()
            db_active_tasks = (
                session.query(ScheduledTask)
                .filter(
                    and_(ScheduledTask.is_active, ScheduledTask.status == TaskStatus.ENABLED.value),
                )
                .count()
            )
            running_tasks = (
                session.query(ScheduledTask)
                .filter(
                    ScheduledTask.status == TaskStatus.RUNNING.value,
                )
                .count()
            )
            error_tasks = (
                session.query(ScheduledTask)
                .filter(
                    ScheduledTask.status == TaskStatus.ERROR.value,
                )
                .count()
            )

            recent_executions = (
                session.query(TaskExecutionLog)
                .filter(
                    TaskExecutionLog.started_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                )
                .count()
            )

            return {
                'total_tasks': db_total_tasks,
                'active_tasks': db_active_tasks,
                'running_tasks': running_tasks,
                'error_tasks': error_tasks,
                'today_executions': recent_executions,
            }
