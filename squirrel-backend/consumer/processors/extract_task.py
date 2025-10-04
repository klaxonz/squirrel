"""
视频提取任务消费者
职责：接收视频提取消息，路由和调度到服务层处理
"""
import logging
from typing import Dict, Any
from pydantic import ValidationError
from common import constants
from models.message import Message
from mq import mq_consumer
from mq.message_router import video_extract_router
from schemas.video.dto.video_dto import VideoExtractDto
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


@mq_consumer(constants.QUEUE_VIDEO_EXTRACT, group="extract", consumer_name="extract-entry")
def process_extract_message(message: Dict[str, Any]) -> None:
    """处理手动视频提取消息（入口队列）"""
    try:
        params = _parse_message(message)
        video_extract_router.route(message, params.url, is_manual=True, is_extract_all=params.is_extract_all)
    except Exception as e:
        logger.error(f"Failed to route manual video extract: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_VIDEO_EXTRACT_SCHEDULED, group="extract", consumer_name="extract-entry-scheduled")
def process_extract_scheduled_message(message: Dict[str, Any]) -> None:
    """处理定时视频提取消息（入口队列，保留用于兼容）"""
    try:
        params = _parse_message(message)
        video_extract_router.route(message, params.url, is_manual=False, is_extract_all=params.is_extract_all)
    except Exception as e:
        logger.error(f"Failed to route scheduled video extract: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_VIDEO_EXTRACT_INCREMENTAL, group="extract", consumer_name="extract-entry-incremental")
def process_extract_incremental_message(message: Dict[str, Any]) -> None:
    """处理增量更新视频提取消息（入口队列，高优先级）"""
    try:
        params = _parse_message(message)
        video_extract_router.route(message, params.url, is_manual=False, is_extract_all=params.is_extract_all)
    except Exception as e:
        logger.error(f"Failed to route incremental video extract: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_VIDEO_EXTRACT_FULL, group="extract", consumer_name="extract-entry-full")
def process_extract_full_message(message: Dict[str, Any]) -> None:
    """处理全量更新视频提取消息（入口队列，低优先级）"""
    try:
        params = _parse_message(message)
        video_extract_router.route(message, params.url, is_manual=False, is_extract_all=params.is_extract_all)
    except Exception as e:
        logger.error(f"Failed to route full video extract: {e}", exc_info=True)


def process_domain_video_extract(message: Dict[str, Any]) -> None:
    """
    处理域特定队列的视频提取任务
    职责：解析消息并调度到服务层处理
    
    注意：此 handler 由消费者配置管理器自动注册
    配置位置：consumer/consumers_setup.py
    """
    params = _parse_message(message)
    video_extractor.extract(params)
