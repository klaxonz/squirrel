"""
重构后的视频提取任务处理器
"""
import logging
from typing import Dict, Any

from crawl import ExtractionTask, ExtractionResult, TaskPriority
from schemas.video.dto.video_dto import VideoExtractDto
from models.message import Message
from mq import mq_consumer
from common import constants
from utils import url_helper
from core.extraction.task_manager import TaskManager
from core.extraction.handlers.video_handler import VideoExtractionHandler
from core.extraction.base import BaseTaskProcessor
from core.extraction.factory import get_extractor_factory

logger = logging.getLogger()


video_handler = VideoExtractionHandler()

# 队列映射配置
QUEUE_MAPPING = {
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

# 初始化任务管理器
task_manager = TaskManager(QUEUE_MAPPING)


# 创建任务处理器
class VideoTaskProcessor(BaseTaskProcessor):
    """视频任务处理器"""

    def __init__(self):
        extractor_factory = get_extractor_factory()
        super().__init__(None, video_handler)
        self.extractor_factory = extractor_factory

    def can_process(self, task: ExtractionTask) -> bool:
        """检查是否可以处理任务"""
        extractor = self.extractor_factory.create_extractor(task.url)
        return extractor is not None

    def process(self, task: ExtractionTask):
        """处理任务"""
        extractor = self.extractor_factory.create_extractor(task.url)
        if not extractor:
            result = ExtractionResult(
                success=False,
                error=f"未找到合适的提取器: {task.url}"
            )
            self.result_handler.handle_failure(task, result)
            return result

        self.extractor = extractor
        return super().process(task)


video_processor = VideoTaskProcessor()
task_manager.add_processor(video_processor)


def route_video_extract(message: Dict[str, Any]) -> str:
    """路由视频提取任务"""
    try:
        message_obj = Message.from_dict(message)
        params = VideoExtractDto.model_validate_json(message_obj.body)

        task = _create_extraction_task(params)

        is_manual = params.is_manual if hasattr(params, 'is_manual') else True
        success, result = task_manager.submit_task(task, is_manual)

        if not success:
            raise ValueError(f"任务提交失败: {result}")

        logger.debug(f"路由视频提取: {params.url} -> {result}")
        return result

    except Exception as e:
        logger.error(f"视频提取路由错误: {e}", exc_info=True)
        raise ValueError("视频提取路由错误")


def _create_extraction_task(params: VideoExtractDto) -> ExtractionTask:
    """创建提取任务"""
    priority = TaskPriority.HIGH if getattr(params, 'is_manual', True) else TaskPriority.NORMAL

    metadata = {
        'subscription_id': params.subscription_id,
        'only_extract': params.only_extract,
        'subscribed': getattr(params, 'subscribed', False),
        'is_extract_all': getattr(params, 'is_extract_all', False),
        'is_manual': getattr(params, 'is_manual', True)
    }

    return task_manager.create_task(
        url=params.url,
        priority=priority,
        metadata=metadata
    )


# 兼容性处理器 - 保持原有的消息队列接口
@mq_consumer(constants.QUEUE_VIDEO_EXTRACT, group="extract", consumer_name="extract-entry")
def process_extract_message(message: Dict[str, Any]):
    """处理提取消息（入口队列）"""
    _process_extract_message_compat(message)


@mq_consumer(constants.QUEUE_VIDEO_EXTRACT_SCHEDULED, group="extract", consumer_name="extract-entry-scheduled")
def process_extract_scheduled_message(message: Dict[str, Any]):
    """处理定时提取消息（入口队列）"""
    _process_extract_message_compat(message)


def _process_extract_message_compat(message: Dict[str, Any]):
    """兼容性消息处理"""
    try:
        logger.debug(f"收到视频解析消息: {message}")
        queue_name = route_video_extract(message)
        from mq.producer import RedisStreamProducer
        RedisStreamProducer().send(queue_name, message)

    except Exception as e:
        logger.error(f"路由失败: {e}", exc_info=True)


@mq_consumer("queue::video::extract::bilibili::manual", group="extract-site")
@mq_consumer("queue::video::extract::bilibili::scheduled", group="extract-site")
@mq_consumer("queue::video::extract::youtube::manual", group="extract-site")
@mq_consumer("queue::video::extract::youtube::scheduled", group="extract-site")
@mq_consumer("queue::video::extract::pornhub::manual", group="extract-site")
@mq_consumer("queue::video::extract::pornhub::scheduled", group="extract-site")
@mq_consumer("queue::video::extract::javdb::manual", group="extract-site")
@mq_consumer("queue::video::extract::javdb::scheduled", group="extract-site")
def process_video_extract_v2(message: Dict[str, Any]):
    """处理视频提取（新版本）"""
    try:
        logger.info(f"开始处理视频解析消息：{message}")

        # 解析消息
        message_obj = Message.from_dict(message)
        params = VideoExtractDto.model_validate_json(message_obj.body)

        # 创建提取任务
        task = _create_extraction_task(params)

        # 处理任务
        result = task_manager.process_task(task)

        platform = url_helper.extract_top_level_domain(params.url)
        logger.info(f"视频提取完成: {result.success} (platform: {platform})")

    except Exception as e:
        logger.error(f"处理消息时发生错误: message: {message}, error: {e}", exc_info=True)


# 导出兼容性函数
__all__ = [
    'process_extract_message',
    'process_extract_scheduled_message',
    'process_video_extract_v2',
    'route_video_extract'
]
