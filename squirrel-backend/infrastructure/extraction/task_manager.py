"""Task manager
"""
import logging
from typing import Any

from .contracts import ExtractionTask, TaskPriority
from .factory import get_extractor_factory

logger = logging.getLogger(__name__)


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
