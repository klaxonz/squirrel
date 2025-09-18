"""
新提取系统配置

在你的应用启动代码中添加以下配置：
"""

from core.extraction import (
    get_extractor_factory, 
    TaskManager, 
    RedisCacheManager, 
    RedisProgressTracker,
    VideoExtractionHandler
)

# 初始化组件
def setup_extraction_system():
    cache_manager = RedisCacheManager("video_extract")
    progress_tracker = RedisProgressTracker(cache_manager)
    video_handler = VideoExtractionHandler()
    
    # 队列映射配置
    queue_mapping = {
        'bilibili': {
            'manual': 'queue::video::extract::bilibili::manual',
            'scheduled': 'queue::video::extract::bilibili::scheduled'
        },
        'youtube': {
            'manual': 'queue::video::extract::youtube::manual', 
            'scheduled': 'queue::video::extract::youtube::scheduled'
        },
        'pornhub': {
            'manual': 'queue::video::extract::pornhub::manual',
            'scheduled': 'queue::video::extract::pornhub::scheduled'
        },
        'javdb': {
            'manual': 'queue::video::extract::javdb::manual',
            'scheduled': 'queue::video::extract::javdb::scheduled'
        }
    }
    
    # 创建任务管理器
    task_manager = TaskManager(cache_manager, progress_tracker, queue_mapping)
    
    return task_manager

# 在应用启动时调用
# task_manager = setup_extraction_system()
