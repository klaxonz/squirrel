"""
视频提取任务处理器
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

# 使用 constants 中已有的映射，避免重复定义
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
    """解析消息"""
    message_obj = Message.from_dict(message)
    return VideoExtractDto.model_validate_json(message_obj.body)


def _resolve_domain_queue(url: str, is_manual: bool) -> str:
    """解析视频 URL 对应的域队列"""
    domain = url_helper.extract_top_level_domain(url)
    mapping = constants.DOMAIN_QUEUE_MAPPING.get(domain)
    if not mapping:
        raise ValueError(f"Unsupported domain for video extract: {domain}")
    
    queue_name = mapping.get('manual' if is_manual else 'scheduled')
    if not queue_name:
        raise ValueError(f"No queue mapping for domain {domain}")
    return queue_name


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


def _route_to_domain_queue(message: Dict[str, Any], is_manual: bool) -> None:
    """将消息路由到域特定队列"""
    params = _parse_message(message)
    queue_name = _resolve_domain_queue(params.url, is_manual)
    
    from mq.producer import RedisStreamProducer
    RedisStreamProducer().send(queue_name, message)


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
        _route_to_domain_queue(message, is_manual=True)
    except Exception as e:
        logger.error(f"Failed to route manual video extract: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_VIDEO_EXTRACT_SCHEDULED, group="extract", consumer_name="extract-entry-scheduled")
def process_extract_scheduled_message(message: Dict[str, Any]) -> None:
    """处理定时视频提取消息（入口队列）"""
    try:
        _route_to_domain_queue(message, is_manual=False)
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
    
    此函数会在模块加载时自动执行，从 constants.SUPPORTED_SITES 读取配置，
    为每个站点的 manual 和 scheduled 队列注册消费者。
    
    优点：
    - 新增站点只需在 constants.SUPPORTED_SITES 添加配置
    - 避免硬编码队列名称
    - 确保所有站点的队列都被正确注册
    """
    from mq.registry import ConsumerRegistry
    
    registered_count = 0
    for site_name in constants.SUPPORTED_SITES.values():
        for mode in ['manual', 'scheduled']:
            queue_name = f'queue::video::extract::{site_name}::{mode}'
            try:
                ConsumerRegistry.register(
                    stream=queue_name,
                    group="extract-domain",
                    consumer_name=f"extract-{site_name}-{mode}",
                    handler=process_domain_video_extract,
                    block_ms=1000,
                    read_count=1
                )
                registered_count += 1
                logger.debug(f"Registered consumer for queue: {queue_name}")
            except Exception as e:
                logger.error(f"Failed to register consumer for {queue_name}: {e}")
    
    logger.info(f"Video extract: registered {registered_count} domain consumers")


# 模块加载时自动注册
# 注意：此代码在模块被导入时执行，由 mq/runner.py 的 module_discovery 触发
_register_domain_consumers()
