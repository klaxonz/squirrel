"""
数据提取核心接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ExtractionResult:
    """数据提取结果"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExtractionTask:
    """数据提取任务"""
    task_id: str
    url: str
    site_name: str
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


class IExtractor(ABC):
    """数据提取器接口"""
    
    @property
    @abstractmethod
    def supported_sites(self) -> List[str]:
        """支持的网站列表"""
        pass
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """判断是否可以处理指定URL"""
        pass
    
    @abstractmethod
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """执行数据提取"""
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """验证URL格式"""
        pass


class ITaskProcessor(ABC):
    """任务处理器接口"""
    
    @abstractmethod
    def process(self, task: ExtractionTask) -> ExtractionResult:
        """处理任务"""
        pass
    
    @abstractmethod
    def can_process(self, task: ExtractionTask) -> bool:
        """判断是否可以处理任务"""
        pass


class IResultHandler(ABC):
    """结果处理器接口"""
    
    @abstractmethod
    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理成功结果"""
        pass
    
    @abstractmethod
    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理失败结果"""
        pass


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


