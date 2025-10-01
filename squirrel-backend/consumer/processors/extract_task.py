"""
视频提取任务消费者
职责：接收视频提取消息，路由和调度到服务层处理
"""
import logging
from typing import Dict, Any
from pydantic import ValidationError

from schemas.video.dto.video_dto import VideoExtractDto
from models.message import Message
from mq import mq_consumer
from mq.message_router import video_extract_router
from mq.consumer_registrar import DomainConsumerRegistrar
from mq.queue_config import QueueType
from common import constants
from services.video_extraction import video_extractor

logger = logging.getLogger()


def _parse_message(message: Dict[str, Any]) -> VideoExtractDto:
    """解析消息为 DTO"""
    try:
        message_obj = Message.from_dict(message)
        return VideoExtractDto.model_validate_json(message_obj.body)
    except ValidationError as e:
        logger.error(f"Failed to parse message: {e}")
        raise


def _process_video_extract(message: Dict[str, Any]) -> None:
    """
    处理视频提取任务
    职责：解析消息并调度到服务层
    """
    params = _parse_message(message)
    video_extractor.extract(params)


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


def process_domain_video_extract(message: Dict[str, Any]) -> None:
    """
    处理域特定队列的视频提取任务
    职责：调度到服务层处理
    """
    try:
        _process_video_extract(message)
    except Exception as e:
        logger.error(f"Failed to process video extract: {e}", exc_info=True)
        raise


def _register_domain_consumers():
    """
    动态注册所有域特定队列的消费者
    
    基于插件注册表自动识别支持的站点，完全消除硬编码
    新增站点只需注册插件即可，无需修改任何配置
    """
    count = DomainConsumerRegistrar.register_all(
        queue_type=QueueType.VIDEO_EXTRACT,
        group='extract-domain',
        consumer_prefix='extract',
        handler=process_domain_video_extract,
        block_ms=1000,
        read_count=1
    )
    logger.info(f"Video extract: registered {count} domain consumers")


# 模块加载时自动注册
_register_domain_consumers()
