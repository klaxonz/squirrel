"""
数据提取核心模块

重构后的数据爬取框架，提供了统一的接口和可扩展的架构。

主要组件：
- interfaces: 核心接口定义
- base: 基础实现类
- factory: 提取器工厂和注册表
- task_manager: 任务管理器
- cache: 缓存管理器
- extractors: 各网站提取器实现
- handlers: 结果处理器
"""

from .interfaces import (
    IExtractor, ITaskProcessor, IResultHandler, ICacheManager,
    ExtractionTask, ExtractionResult, TaskStatus, TaskPriority
)

from .base import BaseExtractor, BaseTaskProcessor, BaseResultHandler

from .factory import (
    ExtractorRegistry, ExtractorFactory, register_extractor,
    get_extractor_factory, get_extractor_registry
)

from .task_manager import TaskManager, TaskRouter, TaskValidator

from .cache import RedisCacheManager, MemoryCacheManager, CacheKeys


# 导入所有提取器以确保注册
from .extractors import (
    bilibili_extractor,
    youtube_extractor,
    pornhub_extractor,
    javdb_extractor
)

from .handlers.video_handler import VideoExtractionHandler

__all__ = [
    # 接口
    'IExtractor', 'ITaskProcessor', 'IResultHandler', 'ICacheManager',
    'ExtractionTask', 'ExtractionResult', 'TaskStatus', 'TaskPriority',
    
    # 基础类
    'BaseExtractor', 'BaseTaskProcessor', 'BaseResultHandler',
    
    # 工厂和注册
    'ExtractorRegistry', 'ExtractorFactory', 'register_extractor',
    'get_extractor_factory', 'get_extractor_registry',
    
    # 任务管理
    'TaskManager', 'TaskRouter', 'TaskValidator',
    
    # 缓存
    'RedisCacheManager', 'MemoryCacheManager', 'CacheKeys',
    
    
    # 处理器
    'VideoExtractionHandler',
]
