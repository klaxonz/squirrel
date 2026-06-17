import logging
from collections.abc import Iterable

from infrastructure.database.session import get_session
from infrastructure.scheduling.base import TaskRegistry
from infrastructure.scheduling.models.scheduled_task import ScheduledTask, TaskStatus, TaskType
from infrastructure.scheduling.store import dynamic_task_manager

logger = logging.getLogger(__name__)


class ScheduledTaskBootstrap:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session

    @staticmethod
    def discover_task_classes() -> None:
        if dynamic_task_manager.task_factory.get_available_task_classes():
            return
        dynamic_task_manager.task_factory.discover_builtin_tasks()

    def ensure_system_tasks(self, task_classes: Iterable[type] | None = None) -> None:
        try:
            self.discover_task_classes()

            classes = list(task_classes) if task_classes is not None else list(TaskRegistry.tasks)
            if not classes:
                return

            default_names = [task_cls.__name__[:100] for task_cls in classes]
            system_names = [f"system_{name}"[:100] for name in default_names]
            candidate_names = default_names + system_names

            # Class paths that should be considered "alive" for orphan detection.
            # Prefer the explicit task_classes argument (covers test/migration scenarios
            # where the caller passes a curated list); otherwise fall back to the
            # factory's discovered builtin registry.
            if task_classes is not None:
                available_classes = {f"{cls.__module__}.{cls.__name__}" for cls in classes}
            else:
                available_classes = set(self._available_task_class_paths())

            with self.session_factory() as session:
                existing_system_tasks = session.query(ScheduledTask).filter(
                    ScheduledTask.task_type == TaskType.SYSTEM.value,
                ).all()
                existing_by_class = {task.task_class: task for task in existing_system_tasks}
                existing_by_name = {
                    task.name: task
                    for task in existing_system_tasks
                    if task.name in candidate_names
                }

                existing_names = {
                    name
                    for (name,) in session.query(ScheduledTask.name)
                    .filter(ScheduledTask.name.in_(candidate_names))
                    .all()
                }

                created_count = 0
                updated_count = 0

                for task_cls in classes:
                    task_class = f"{task_cls.__module__}.{task_cls.__name__}"
                    existing_task = (
                        existing_by_class.get(task_class)
                        or existing_by_name.get(task_cls.__name__[:100])
                        or existing_by_name.get(f"system_{task_cls.__name__[:100]}"[:100])
                    )
                    if existing_task:
                        if existing_task.task_class != task_class:
                            existing_task.task_class = task_class
                            existing_task.status = TaskStatus.ENABLED.value
                            existing_task.last_error = None
                            updated_count += 1
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

                # Drop system tasks whose backing class is gone.
                # Runs after the update loop so tasks that were merely renamed/module-moved
                # have already had their task_class refreshed and won't be treated as orphans.
                orphaned = [
                    task for task in existing_system_tasks
                    if task.task_class not in available_classes
                ]
                for task in orphaned:
                    logger.info('Removing orphaned system task %s (class %s no longer exists)', task.name, task.task_class)
                    session.delete(task)

                if created_count:
                    logger.info("Bootstrap created %s system scheduled tasks", created_count)
                if updated_count:
                    logger.info("Bootstrap updated %s system scheduled task classes", updated_count)
        except Exception as e:
            logger.error("Failed to ensure system tasks: %s", e, exc_info=True)

    @staticmethod
    def _available_task_class_paths() -> set[str]:
        """Return the set of registered task class paths (module.ClassName)."""
        return set(dynamic_task_manager.task_factory.get_available_task_classes().keys())


scheduled_task_bootstrap = ScheduledTaskBootstrap()
discover_task_classes = scheduled_task_bootstrap.discover_task_classes
ensure_system_tasks = scheduled_task_bootstrap.ensure_system_tasks
