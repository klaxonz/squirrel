"""
任务管理器
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from .contracts import ExtractionTask, TaskPriority
from .factory import get_extractor_factory

logger = logging.getLogger(__name__)


class ICacheManager(ABC):
    """缓存管理器接口"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除缓存"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass


class TaskManager:
    """任务管理器"""

    def create_task(self,
                    url: str,
                    site_name: Optional[str] = None,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    metadata: Optional[dict[str, Any]] = None) -> ExtractionTask:
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
            metadata=metadata or {}
        )
