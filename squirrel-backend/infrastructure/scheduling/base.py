import logging
from typing import ClassVar

logger = logging.getLogger(__name__)


class BaseTask:
    interval: int = 60
    unit: str = 'seconds'
    start_immediately: bool = True

    @classmethod
    def run(cls):
        raise NotImplementedError('Subclasses must implement run method')


class TaskRegistry:
    tasks: ClassVar[list[type[BaseTask]]] = []

    @classmethod
    def register(cls, interval: int, unit: str = 'seconds', start_immediately: bool = True):
        def decorator(task_class):
            task_class.interval = interval
            task_class.unit = unit
            task_class.start_immediately = start_immediately
            cls.tasks.append(task_class)
            return task_class

        return decorator
