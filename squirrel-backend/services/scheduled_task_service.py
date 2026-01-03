import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import or_, and_, desc
from sqlalchemy.orm import selectinload

from core.database import get_session
from models.scheduled_task import ScheduledTask, TaskExecutionLog, TaskStatus, TaskType
from core.dynamic_task_manager import dynamic_task_manager

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
        """获取任务列表（包含数据库任务和传统任务）"""
        from models.scheduler_status import SchedulerStatus

        all_tasks = []

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
            all_tasks.extend([task.to_dict() for task in db_tasks])

            legacy_tasks = []
            if not task_type or task_type == 'system':
                scheduler_status = session.query(SchedulerStatus).filter(
                    SchedulerStatus.process_name == 'scheduler'
                ).first()

                if scheduler_status and scheduler_status.legacy_tasks:
                    for task_name, task_info in scheduler_status.legacy_tasks.items():
                        if search and search.lower() not in task_name.lower() and search.lower() not in task_info.get('description', '').lower():
                            continue

                        legacy_task = {
                            'id': f'legacy_{task_name}',
                            'name': task_info.get('name', task_name),
                            'task_type': 'system',
                            'description': task_info.get('description', ''),
                            'interval': task_info.get('interval', 60),
                            'unit': task_info.get('unit', 'seconds'),
                            'start_immediately': task_info.get('start_immediately', True),
                            'status': 'enabled',
                            'is_active': True,
                            'task_class': task_info.get('task_class', ''),
                            'task_params': {},
                            'last_run_at': None,
                            'next_run_at': None,
                            'last_error': None,
                            'run_count': 0,
                            'success_count': 0,
                            'error_count': 0,
                            'created_at': None,
                            'updated_at': None,
                            'is_legacy': True
                        }
                        legacy_tasks.append(legacy_task)

            all_tasks.extend(legacy_tasks)

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
    def get_task_by_id(task_id: int) -> Optional[ScheduledTask]:
        """根据ID获取任务"""
        with get_session() as session:
            return session.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()

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

                # 注册到动态任务管理器
                if is_active:
                    dynamic_task_manager.add_task(task_config)

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

                # 更新动态任务管理器
                dynamic_task_manager.update_task(task_config)

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

                # 从动态任务管理器移除
                dynamic_task_manager.remove_task(task_id)

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

                # 创建手动执行日志
                execution_log = TaskExecutionLog(
                    task_id=task_id,
                    task_name=task_config.name,
                    started_at=datetime.now(),
                    status='manual_trigger',
                    executed_by=executed_by or 'manual'
                )
                session.add(execution_log)
                session.commit()

            # 触发执行
            return dynamic_task_manager.execute_task_now(task_id)

        except Exception as e:
            logger.error(f"Failed to execute task {task_id} now: {e}")
            return False

    @staticmethod
    def get_available_task_classes() -> Dict[str, Any]:
        """获取可用的任务类"""
        return dynamic_task_manager.task_factory.get_available_task_classes()

    @staticmethod
    def get_task_execution_logs(
        task_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取任务执行日志"""
        with get_session() as session:
            query = session.query(TaskExecutionLog)

            if task_id:
                query = query.filter(TaskExecutionLog.task_id == task_id)

            if status:
                query = query.filter(TaskExecutionLog.status == status)

            query = query.order_by(desc(TaskExecutionLog.started_at))

            total = query.count()
            logs = query.offset((page - 1) * page_size).limit(page_size).all()

            return {
                "page": page,
                "page_size": page_size,
                "total": total,
                "data": [log.to_dict() for log in logs]
            }

    @staticmethod
    def get_task_statistics() -> Dict[str, Any]:
        """获取任务统计信息（包含传统任务）"""
        from models.scheduler_status import SchedulerStatus

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

            legacy_task_count = 0
            scheduler_status = session.query(SchedulerStatus).filter(
                SchedulerStatus.process_name == 'scheduler'
            ).first()
            if scheduler_status and scheduler_status.legacy_tasks:
                legacy_task_count = len(scheduler_status.legacy_tasks)

            return {
                "total_tasks": db_total_tasks + legacy_task_count,
                "active_tasks": db_active_tasks + legacy_task_count,
                "running_tasks": running_tasks,
                "error_tasks": error_tasks,
                "today_executions": recent_executions
            }


# 服务实例
scheduled_task_service = ScheduledTaskService()
