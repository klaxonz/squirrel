"""数据提取核心模块

重构后的数据爬取框架，提供了统一的接口和可扩展的架构。

主要组件：
- interfaces: 核心接口定义
- base: 基础实现类
- factory: 提取器工厂
- task_manager: 任务管理器
- cache: 缓存管理器
- extractors: 各网站提取器实现
- handlers: 结果处理器
"""


from .base import BaseExtractor, BaseResultHandler, BaseTaskProcessor
from .contracts import (
    ExtractionResult,
    ExtractionTask,
    Extractor,
    ResultHandler,
    TaskPriority,
    TaskProcessor,
    TaskStatus,
)
from .factory import (
    ExtractorFactory,
    get_extractor_factory,
    reset_factory,
)
from .handlers.video_handler import VideoExtractionHandler
from .runtime_payloads import RuntimeActorData, RuntimeVideoData
from .task_manager import TaskManager

__all__ = [
    "TaskStatus",
    "TaskPriority",
    "ExtractionTask",
    "ExtractionResult",
    "Extractor",
    "TaskProcessor",
    "ResultHandler",
    "RuntimeVideoData",
    "RuntimeActorData",
    # 基础类
    "BaseExtractor", "BaseTaskProcessor", "BaseResultHandler",

    # 工厂和注册
    "ExtractorFactory",
    "get_extractor_factory",
    "reset_factory",

    # 任务管理
    "TaskManager",

    # 处理器
    "VideoExtractionHandler",
]
