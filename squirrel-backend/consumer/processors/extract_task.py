"""
视频提取任务消费者
职责：接收域队列的视频提取消息，调度到服务层处理
"""
import logging
from typing import Dict, Any
from pydantic import ValidationError
from models.message import Message
from schemas.video.dto.video_dto import VideoExtractDto
from services.video_extraction import extract_video

logger = logging.getLogger()


def _parse_message(message: Dict[str, Any]) -> VideoExtractDto:
    """解析消息为 DTO"""
    try:
        message_obj = Message.from_dict(message)
        return VideoExtractDto.model_validate_json(message_obj.body)
    except ValidationError as e:
        logger.error(f"Failed to parse message: {e}")
        raise


def process_domain_video_extract(message: Dict[str, Any]) -> None:
    """
    处理域特定队列的视频提取任务
    职责：解析消息并调度到服务层处理
    
    注意：此 handler 由消费者配置管理器自动注册
    配置位置：consumer/consumers_setup.py
    """
    params = _parse_message(message)
    extract_video(params)
