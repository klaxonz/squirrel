"""
视频提取任务处理器
"""
import logging
from typing import Dict, Any
from pydantic import ValidationError

from crawl import ExtractionTask, ExtractionResult, TaskPriority
from schemas.video.dto.video_dto import VideoExtractDto
from models.message import Message
from mq import mq_consumer
from mq.message_router import video_extract_router
from mq.consumer_registrar import DomainConsumerRegistrar
from common import constants
from utils import url_helper
from core.extraction.task_manager import TaskManager
from core.extraction.handlers.video_handler import VideoExtractionHandler
from core.extraction.base import BaseTaskProcessor
from core.extraction.factory import get_extractor_factory

logger = logging.getLogger()

video_handler = VideoExtractionHandler()
task_manager = TaskManager(constants.DOMAIN_QUEUE_MAPPING)


# 创建任务处理器
class VideoTaskProcessor(BaseTaskProcessor):
    """视频任务处理器"""

    def __init__(self):
        extractor_factory = get_extractor_factory()
        super().__init__(None, video_handler)
        self.extractor_factory = extractor_factory

    def _get_extractor_for_task(self, task: ExtractionTask):
        return self.extractor_factory.create_extractor(task.url)

    def can_process(self, task: ExtractionTask) -> bool:
        """检查是否可以处理任务"""
        extractor = self.extractor_factory.create_extractor(task.url)
        return extractor is not None

    def process(self, task: ExtractionTask):
        """处理任务"""
        extractor = self._get_extractor_for_task(task)
        if not extractor:
            result = ExtractionResult(
                success=False,
                error=f"未找到合适的提取器: {task.url}"
            )
            self.result_handler.handle_failure(task, result)
            return result

        return super()._process_with_extractor(extractor, task)


video_processor = VideoTaskProcessor()
task_manager.add_processor(video_processor)


def _parse_message(message: Dict[str, Any]) -> VideoExtractDto:
    """解析消息为 DTO"""
    try:
        # 从 Message 对象解析
        message_obj = Message.from_dict(message)
        return VideoExtractDto.model_validate_json(message_obj.body)
    except ValidationError as e:
        logger.error(f"Failed to parse message: {e}")
        raise


def _create_extraction_task(params: VideoExtractDto) -> ExtractionTask:
    """创建提取任务"""
    priority = TaskPriority.HIGH if params.is_manual else TaskPriority.NORMAL

    metadata = {
        'subscription_id': params.subscription_id,
        'only_extract': params.only_extract,
        'subscribed': params.subscribed,
        'is_extract_all': params.is_extract_all,
        'is_manual': params.is_manual
    }

    return task_manager.create_task(
        url=params.url,
        priority=priority,
        metadata=metadata
    )




def _process_video_extract(message: Dict[str, Any]) -> None:
    """处理视频提取任务"""
    params = _parse_message(message)
    
    logger.info(f"Processing video extract: {params.url}")
    
    task = _create_extraction_task(params)
    result = task_manager.process_task(task)
    
    platform = url_helper.extract_top_level_domain(params.url)
    logger.info(f"Video extract completed: {result.success} (platform: {platform})")


# 入口队列消费者：路由到域特定队列
@mq_consumer(constants.QUEUE_VIDEO_EXTRACT, group="extract", consumer_name="extract-entry")
def process_extract_message(message: Dict[str, Any]) -> None:
    """处理手动视频提取消息（入口队列）"""
    try:
        params = _parse_message(message)
        video_extract_router.route(message, params.url, is_manual=True)
    except Exception as e:
        logger.error(f"Failed to route manual video extract: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_VIDEO_EXTRACT_SCHEDULED, group="extract", consumer_name="extract-entry-scheduled")
def process_extract_scheduled_message(message: Dict[str, Any]) -> None:
    """处理定时视频提取消息（入口队列）"""
    try:
        params = _parse_message(message)
        video_extract_router.route(message, params.url, is_manual=False)
    except Exception as e:
        logger.error(f"Failed to route scheduled video extract: {e}", exc_info=True)


# 域队列消费者：实际处理视频提取
def process_domain_video_extract(message: Dict[str, Any]) -> None:
    """处理域特定队列的视频提取任务"""
    try:
        _process_video_extract(message)
    except Exception as e:
        logger.error(f"Failed to process video extract: {e}", exc_info=True)
        raise


# 动态注册所有域队列消费者
def _register_domain_consumers():
    """
    动态注册所有域特定队列的消费者
    
    使用统一的 DomainConsumerRegistrar 简化注册逻辑
    新增站点只需在 constants.SUPPORTED_SITES 添加配置即可
    """
    count = DomainConsumerRegistrar.register_all(
        queue_template='queue::video::extract::{site}::{mode}',
        group='extract-domain',
        consumer_prefix='extract',
        handler=process_domain_video_extract,
        block_ms=1000,
        read_count=1
    )
    logger.info(f"Video extract: registered {count} domain consumers")


# 模块加载时自动注册
# 注意：此代码在模块被导入时执行，由 mq/runner.py 的 module_discovery 触发
_register_domain_consumers()
