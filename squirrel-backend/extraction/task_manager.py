"""Task manager
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from .contracts import ExtractionTask, TaskPriority
from .factory import get_extractor_factory

logger = logging.getLogger(__name__)


class ICacheManager(ABC):
    """Cache manager interface"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Get cached value"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set cached value"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete cached value"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if cache key exists"""


class TaskManager:
    """Task manager"""

    def create_task(self,
                    url: str,
                    site_name: str | None = None,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    metadata: dict[str, Any] | None = None) -> ExtractionTask:
        """Create extraction task"""
        # Infer site name from URL if not provided
        if not site_name:
            extractor = get_extractor_factory().create_extractor(url)
            if extractor and extractor.site_name:
                site_name = extractor.site_name

        return ExtractionTask(
            url=url,
            site_name=site_name or "unknown",
            priority=priority,
            metadata=metadata or {},
        )
