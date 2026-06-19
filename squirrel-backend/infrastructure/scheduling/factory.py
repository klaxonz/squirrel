import logging
from threading import Lock
from typing import Any

from infrastructure.scheduling.base import BaseTask
from infrastructure.scheduling.models.scheduled_task import ScheduledTask
from shared_kernel.infrastructure import module_discovery

logger = logging.getLogger(__name__)


class TaskFactory:
    """Task factory class responsible for dynamically creating task instances."""

    def __init__(self):
        self._task_classes: dict[str, type[BaseTask]] = {}
        self._lock = Lock()

    def discover_builtin_tasks(self) -> None:
        """Discover and register built-in tasks."""
        try:
            task_classes = module_discovery.import_classes_from_package(
                'workers.scheduling.tasks',
                base_class=BaseTask,
                recursive=True,
            )

            with self._lock:
                for task_class in task_classes:
                    if task_class is BaseTask:
                        continue
                    task_name = f'{task_class.__module__}.{task_class.__name__}'
                    self._task_classes[task_name] = task_class
                    logger.info('Discovered builtin task: %s', task_name)
        except ImportError as e:
            logger.error('Failed to discover builtin tasks: %s', e)

    def register_task_class(self, task_class: type[BaseTask], task_name: str | None = None) -> None:
        """Register a task class."""
        if task_name is None:
            task_name = f'{task_class.__module__}.{task_class.__name__}'

        with self._lock:
            self._task_classes[task_name] = task_class
            logger.info('Registered task class: %s', task_name)

    def get_task_class(self, task_class_name: str) -> type[BaseTask] | None:
        """Get a task class."""
        with self._lock:
            return self._task_classes.get(task_class_name)

    def create_task_instance(self, task_config: ScheduledTask) -> BaseTask | None:
        """Create a task instance from configuration."""
        task_class = self.get_task_class(task_config.task_class)
        if not task_class:
            logger.error('Task class not found: %s', task_config.task_class)
            return None

        try:
            task_instance = task_class()
            task_instance.interval = task_config.interval
            task_instance.unit = task_config.unit
            task_instance.start_immediately = task_config.start_immediately

            if task_config.task_params:
                for key, value in task_config.task_params.items():
                    if hasattr(task_instance, key):
                        setattr(task_instance, key, value)

            return task_instance
        except (TypeError, ValueError, AttributeError) as e:
            logger.error('Failed to create task instance for %s: %s', task_config.name, e)
            return None

    def get_available_task_classes(self) -> dict[str, dict[str, Any]]:
        """Get information about all available task classes."""
        context = {}
        with self._lock:
            for task_name, task_class in self._task_classes.items():
                context[task_name] = {
                    'name': task_name,
                    'description': (getattr(task_class, '__doc__', '') or '').strip() or 'No description',
                    'module': task_class.__module__,
                    'class_name': task_class.__name__,
                    'default_interval': getattr(task_class, 'interval', 60),
                    'default_unit': getattr(task_class, 'unit', 'seconds'),
                    'default_start_immediately': getattr(task_class, 'start_immediately', True),
                }
        return context
