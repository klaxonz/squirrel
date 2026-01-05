import logging
from typing import Iterable

from core.database import get_session
from core.dynamic_task_manager import dynamic_task_manager
from models.scheduled_task import ScheduledTask, TaskType, TaskStatus
from schedule.task import TaskRegistry

logger = logging.getLogger(__name__)


def discover_task_classes() -> None:
    if dynamic_task_manager.task_factory.get_available_task_classes():
        return
    dynamic_task_manager.task_factory.discover_builtin_tasks()


def ensure_system_tasks(task_classes: Iterable[type] | None = None) -> None:
    try:
        discover_task_classes()

        classes = list(task_classes) if task_classes is not None else list(TaskRegistry.tasks)
        if not classes:
            return

        with get_session() as session:
            existing_system_tasks = session.query(ScheduledTask).filter(
                ScheduledTask.task_type == TaskType.SYSTEM.value
            ).all()
            existing_by_class = {task.task_class: task for task in existing_system_tasks}

            existing_names = {name for (name,) in session.query(ScheduledTask.name).all()}

            created_count = 0

            for task_cls in classes:
                task_class = f"{task_cls.__module__}.{task_cls.__name__}"
                if task_class in existing_by_class:
                    continue

                name = task_cls.__name__
                if name in existing_names:
                    name = f"system_{name}"
                    name = name[:100]

                existing_names.add(name)

                description = (task_cls.__doc__ or "").strip() or None
                interval = int(getattr(task_cls, "interval", 60))
                unit = str(getattr(task_cls, "unit", "seconds"))
                start_immediately = bool(getattr(task_cls, "start_immediately", True))

                task = ScheduledTask(
                    name=name,
                    task_type=TaskType.SYSTEM.value,
                    description=description,
                    interval=interval,
                    unit=unit,
                    start_immediately=start_immediately,
                    max_retries=3,
                    status=TaskStatus.ENABLED.value,
                    is_active=True,
                    task_class=task_class,
                    task_params={},
                    created_by="system",
                    updated_by="system",
                )
                session.add(task)
                created_count += 1

            if created_count:
                logger.info(f"Bootstrap created {created_count} system scheduled tasks")
    except Exception as e:
        logger.error(f"Failed to ensure system tasks: {e}", exc_info=True)
