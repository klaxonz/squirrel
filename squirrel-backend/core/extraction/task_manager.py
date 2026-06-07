"""任务管理器
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from .contracts import ExtractionTask, TaskPriority
from .factory import get_extractor_factory

logger = logging.getLogger(__name__)


class ICacheManager(ABC):
    """缓存管理器接口"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存"""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""


class TaskManager:
    """任务管理器"""

    def create_task(self,
                    url: str,
                    site_name: str | None = None,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    metadata: dict[str, Any] | None = None) -> ExtractionTask:
        """创建提取任务"""
        # 如果没有指定网站名，尝试从URL推断
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
