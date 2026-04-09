import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import or_, and_, desc

from core.database import get_session
from models.scheduled_task import ScheduledTask, TaskExecutionLog, TaskStatus, TaskType
from core.dynamic_task_manager import dynamic_task_manager
from services.scheduled_task_bootstrap import ensure_system_tasks, discover_task_classes

logger = logging.getLogger(__name__)


class ScheduledTaskService:
    """定时任务服务"""

    @staticmethod
    def get_task_list(
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取任务列表"""
        ensure_system_tasks()

        with get_session() as session:
            db_tasks = session.query(ScheduledTask)

            if search:
                db_tasks = db_tasks.filter(
                    or_(
                        ScheduledTask.name.ilike(f"%{search}%"),
                        ScheduledTask.description.ilike(f"%{search}%")
                    )
                )

            if status:
                db_tasks = db_tasks.filter(ScheduledTask.status == status)

            if task_type:
                db_tasks = db_tasks.filter(ScheduledTask.task_type == task_type)

            db_tasks = db_tasks.order_by(desc(ScheduledTask.created_at)).all()
            all_tasks = [task.to_dict() for task in db_tasks]

        total = len(all_tasks)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tasks = all_tasks[start_idx:end_idx]

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "data": paginated_tasks
        }

    @staticmethod
    def create_task(
        name: str,
        task_class: str,
        task_type: str = TaskType.USER.value,
        description: Optional[str] = None,
        interval: int = 60,
        unit: str = 'seconds',
        start_immediately: bool = True,
        max_retries: int = 3,
        task_params: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
        created_by: Optional[str] = None
    ) -> Optional[ScheduledTask]:
        """创建新任务"""
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
                updated_by=created_by
            )

            with get_session() as session:
                session.add(task_config)
                session.commit()
                session.refresh(task_config)

                logger.info(f"Created scheduled task: {name} (ID: {task_config.id})")
                return task_config

        except Exception as e:
            logger.error(f"Failed to create task {name}: {e}")
            return None

    @staticmethod
    def update_task(
        task_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        interval: Optional[int] = None,
        unit: Optional[str] = None,
        start_immediately: Optional[bool] = None,
        max_retries: Optional[int] = None,
        task_params: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[str] = None
    ) -> bool:
        """更新任务配置"""
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

                logger.info(f"Updated scheduled task: {task_config.name} (ID: {task_id})")
                return True

        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False

    @staticmethod
    def delete_task(task_id: int) -> bool:
        """删除任务"""
        try:
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return False

                if task_config.task_type == TaskType.SYSTEM.value:
                    logger.warning(f"Refuse to delete system task: {task_config.name} (ID: {task_id})")
                    return False

                # 删除任务记录
                session.delete(task_config)
                session.commit()

                logger.info(f"Deleted scheduled task: {task_config.name} (ID: {task_id})")
                return True

        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False

    @staticmethod
    def enable_task(task_id: int, updated_by: Optional[str] = None) -> bool:
        """启用任务"""
        return ScheduledTaskService.update_task(
            task_id=task_id,
            is_active=True,
            updated_by=updated_by
        )

    @staticmethod
    def disable_task(task_id: int, updated_by: Optional[str] = None) -> bool:
        """禁用任务"""
        return ScheduledTaskService.update_task(
            task_id=task_id,
            is_active=False,
            updated_by=updated_by
        )

    @staticmethod
    def execute_task_now(task_id: int, executed_by: Optional[str] = None) -> bool:
        """立即执行任务"""
        try:
            # 记录执行请求
            with get_session() as session:
                task_config = session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if not task_config:
                    return False

                # 创建手动执行请求（由 scheduler 进程消费并执行）
                execution_log = TaskExecutionLog(
                    task_id=task_id,
                    task_name=task_config.name,
                    started_at=datetime.now(),
                    status='manual_trigger',
                    executed_by=executed_by or 'manual'
                )
                session.add(execution_log)
                session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to execute task {task_id} now: {e}")    
            return False

    @staticmethod
    def get_available_task_classes() -> Dict[str, Any]:
        """获取可用的任务类"""
        discover_task_classes()
        return dynamic_task_manager.task_factory.get_available_task_classes()

    @staticmethod
    def get_task_statistics() -> Dict[str, Any]:
        """获取任务统计信息"""
        ensure_system_tasks()

        with get_session() as session:
            db_total_tasks = session.query(ScheduledTask).count()
            db_active_tasks = session.query(ScheduledTask).filter(
                and_(ScheduledTask.is_active == True, ScheduledTask.status == TaskStatus.ENABLED.value)
            ).count()
            running_tasks = session.query(ScheduledTask).filter(
                ScheduledTask.status == TaskStatus.RUNNING.value
            ).count()
            error_tasks = session.query(ScheduledTask).filter(
                ScheduledTask.status == TaskStatus.ERROR.value
            ).count()

            recent_executions = session.query(TaskExecutionLog).filter(
                TaskExecutionLog.started_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            ).count()

            return {
                "total_tasks": db_total_tasks,
                "active_tasks": db_active_tasks,
                "running_tasks": running_tasks,
                "error_tasks": error_tasks,
                "today_executions": recent_executions
            }

