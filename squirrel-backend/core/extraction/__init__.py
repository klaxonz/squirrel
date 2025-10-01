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


from .base import BaseExtractor, BaseTaskProcessor, BaseResultHandler

from .factory import (
    ExtractorRegistry, ExtractorFactory, register_extractor,
    get_extractor_factory, get_extractor_registry
)
from .plugin_bridge import (
    initialize_plugin_bridge, refresh_plugin_bridge, get_plugin_bridge
)

from .task_manager import TaskManager, TaskRouter

from .handlers.video_handler import VideoExtractionHandler

__all__ = [
    # 基础类
    'BaseExtractor', 'BaseTaskProcessor', 'BaseResultHandler',
    
    # 工厂和注册
    'ExtractorRegistry', 'ExtractorFactory', 'register_extractor',
    'get_extractor_factory', 'get_extractor_registry',
    
    # 插件桥接
    'initialize_plugin_bridge', 'refresh_plugin_bridge', 'get_plugin_bridge',
    
    # 任务管理
    'TaskManager', 'TaskRouter',
    
    # 处理器
    'VideoExtractionHandler',
]
