"""
任务管理器
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from crawl import ExtractionTask, ITaskProcessor, TaskPriority, ExtractionResult
from .factory import get_extractor_factory

logger = logging.getLogger()


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


class TaskRouter:
    """任务路由器"""

    def __init__(self, queue_mapping: Dict[str, Dict[str, str]]):
        self.queue_mapping = queue_mapping

    def get_queue_name(self, site_name: str, is_manual: bool = True) -> Optional[str]:
        """获取队列名称"""
        if site_name not in self.queue_mapping:
            return None

        queue_type = 'manual' if is_manual else 'scheduled'
        return self.queue_mapping[site_name].get(queue_type)

    def route_task(self, task: ExtractionTask, is_manual: bool = True) -> Optional[str]:
        """路由任务到合适的队列"""
        try:
            extractor = get_extractor_factory().create_extractor(task.url)
            if not extractor:
                logger.error(f"无法为URL创建提取器: {task.url}")
                return None

            site_name = extractor.supported_sites[0] if extractor.supported_sites else None
            if not site_name:
                logger.error(f"提取器未指定网站名: {task.url}")
                return None

            queue_name = self.get_queue_name(site_name, is_manual)
            if not queue_name:
                logger.error(f"未找到队列映射: {site_name}")
                return None

            logger.debug(f"任务路由: {task.url} -> {queue_name}")
            return queue_name

        except Exception as e:
            logger.error(f"任务路由失败: {task.url}, error: {e}")
            return None


class TaskManager:
    """任务管理器"""

    def __init__(self, queue_mapping: Optional[Dict[str, Dict[str, str]]] = None):
        """
        Args:
            queue_mapping: 队列映射（已废弃，保留用于兼容性）
        """
        self.router = TaskRouter(queue_mapping or {})
        self._processors: List[ITaskProcessor] = []

    def add_processor(self, processor: ITaskProcessor) -> None:
        """添加任务处理器"""
        self._processors.append(processor)

    def create_task(self,
                    url: str,
                    site_name: Optional[str] = None,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    metadata: Optional[Dict[str, Any]] = None) -> ExtractionTask:
        """创建提取任务"""

        # 如果没有指定网站名，尝试从URL推断
        if not site_name:
            extractor = get_extractor_factory().create_extractor(url)
            if extractor and extractor.supported_sites:
                site_name = extractor.supported_sites[0]

        return ExtractionTask(
            url=url,
            site_name=site_name or "unknown",
            priority=priority,
            metadata=metadata or {}
        )

    def submit_task(self, task: ExtractionTask, is_manual: bool = True) -> tuple[bool, Optional[str]]:
        """提交任务"""
        try:
            queue_name = self.router.route_task(task, is_manual)
            if not queue_name:
                return False, "任务路由失败"

            logger.debug(f"任务提交成功: {task.task_id}, queue: {queue_name}")
            return True, queue_name

        except Exception as e:
            logger.error(f"提交任务失败: {task.task_id}, error: {e}")
            return False, str(e)

    def process_task(self, task: ExtractionTask) -> ExtractionResult:
        try:
            processor = None
            for p in self._processors:
                if p.can_process(task):
                    processor = p
                    break

            if not processor:
                error_msg = f"未找到合适的处理器: {task.url}"
                logger.error(error_msg)
                result = ExtractionResult(success=False, error=error_msg)
            else:
                result = processor.process(task)

            return result

        except Exception as e:
            error_msg = f"处理任务异常: {task.task_id}, error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return ExtractionResult(success=False, error=error_msg)
