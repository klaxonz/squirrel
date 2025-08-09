import logging
from datetime import datetime
from typing import Dict, Any
from cache import task_cache
from common import constants
from core.database import get_session
from downloader.factory import DownloaderFactory
from dto.video_dto import VideoExtractDto
from meta.factory import VideoFactory
from models.message import Message
from services import (
    video_service, task_service, message_service, subscription_video_service,
    creator_service, video_creator_service, subscription_service
)
from utils import url_helper
from consumer.queue_management.decorators import queue_handler, routing_rule
from consumer.queue_management.router import MessageRouter
from consumer.queue_management.manager import QueueManager
from consumer.queue_management.exceptions import RoutingError
from common.types.queues import ExtractQueueType


logger = logging.getLogger(__name__)


def get_queue_type(params: VideoExtractDto) -> ExtractQueueType:
    return ExtractQueueType.SCHEDULED if params.only_extract else ExtractQueueType.FOR_DOWNLOAD


def _resolve_extract_queue(params: VideoExtractDto) -> str:
    domain = url_helper.extract_top_level_domain(params.url)
    mapping = constants.DOMAIN_QUEUE_MAPPING.get(domain)
    if not mapping:
        raise RoutingError(
            f"Unsupported domain for extract: {domain}",
            rule_name="video_extract",
        )

    queue_type = get_queue_type(params)
    queue_name = mapping.get(queue_type.value)
    if not queue_name:
        raise RoutingError(
            f"No queue mapping for domain {domain} and type {queue_type.value}",
            rule_name="video_extract",
        )
    return queue_name


@routing_rule("video_extract")
def route_video_extract(message: Dict[str, Any]) -> str:
    try:
        message_obj = Message.from_dict(message)
        params = VideoExtractDto.model_validate_json(message_obj.body)

        queue_name = _resolve_extract_queue(params)
        logger.debug(f"Routed video extract: {params.url} -> {queue_name}")
        return queue_name

    except Exception as e:
        logger.error(f"Error in video extract routing: {e}", exc_info=True)
        raise RoutingError(
            "Error in video extract routing",
            rule_name="video_extract",
            original_message=message,
            cause=e
        )


@queue_handler(constants.QUEUE_VIDEO_EXTRACT)
def process_extract_message(message: Dict[str, Any]):
    _process_extract_message_compat(message)


@queue_handler(constants.QUEUE_VIDEO_EXTRACT_SCHEDULED)
def process_extract_scheduled_message(message: Dict[str, Any]):
    _process_extract_message_compat(message)


def _process_extract_message_compat(message: Dict[str, Any]):
    params = None
    try:
        logger.info(f"收到视频解析消息: {message}")

        message_obj = Message.from_dict(message)
        params = VideoExtractDto.model_validate_json(message_obj.body)

        if not _check_subscription_exist(params.subscription_id):
            logger.warning(f"Subscription {params.subscription_id} not found or deleted")
            return

        MessageRouter.send_with_routing("video_extract", message)

    except Exception as e:
        logger.error(f"路由失败，严格失败: {e}", exc_info=True)
        if params and hasattr(params, 'url') and params.url:
            task_cache.delete_extract_cache(params.url, constants.VIDEO_EXTRACT_FIELD_NAME)
        raise


@queue_handler("video_extract_*")
def process_video_extract(message: Dict[str, Any], queue_name: str):
    params = None
    try:
        logger.info(f"开始处理视频解析消息：{message} (queue: {queue_name})")

        queue_parts = queue_name.split('_')
        platform = queue_parts[2] if len(queue_parts) > 2 else 'unknown'
        queue_type = ExtractQueueType.SCHEDULED if 'scheduled' in queue_name else ExtractQueueType.FOR_DOWNLOAD

        message_obj = Message.from_dict(message)
        params = VideoExtractDto.model_validate_json(message_obj.body)

        if not _check_subscription_exist(params.subscription_id):
            logger.warning(f"Subscription {params.subscription_id} not found or deleted")
            return

        video_info = _get_video_info(params.url, queue_name)
        if not video_info:
            logger.info(f"{params.url} is not a valid video, skip")
            return

        video_meta = VideoFactory.create_video(params.url, video_info)

        video = _handle_video_extraction(params, video_meta, video_info)

        task_cache.delete_extract_cache(params.url, constants.VIDEO_EXTRACT_FIELD_NAME)

        if not params.only_extract and video:
            _handle_download_task(video)

        logger.info(f"视频提取完成: {video.title if video else 'N/A'} (platform: {platform}, type: {queue_type})")

    except Exception as e:
        logger.error(f"处理消息时发生错误: message: {message}, queue: {queue_name}, error: {e}", exc_info=True)
    finally:
        if params and params.url:
            task_cache.delete_extract_cache(params.url, constants.VIDEO_EXTRACT_FIELD_NAME)


def _get_video_info(url, queue_name: str):
    downloader = DownloaderFactory.create_downloader(url)
    video_info = downloader.get_video_info(url, queue_name)
    if video_info is None or ('_type' in video_info and video_info['_type'] == 'playlist'):
        logger.info(f"{url} is not a valid video, skip")
        return None
    return video_info


def _create_video(params: VideoExtractDto, video_meta, video_info):
    with get_session():
        video = video_service.get_video_by_url(video_meta.url)
        if not video:
            video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
            video = video_service.create_video(video_meta.url, video_info['title'], video_info['publish_date'],
                                               video_info['thumbnail'], video_info['duration'])
        subscription_video = subscription_video_service.get_subscription_video(params.subscription_id, video.id)
        if not subscription_video:
            subscription_video_service.create_subscription_video(params.subscription_id, video.id)

        actors = video_meta.actors
        if len(actors) > 0:
            for actor_meta in actors:
                creator = creator_service.get_creator_by_url(actor_meta.url)
                if not creator:
                    creator = creator_service.create_creator(actor_meta.url, actor_meta.name, actor_meta.avatar)
                video_creator = video_creator_service.get_video_creator(video.id, creator.id)
                if not video_creator:
                    video_creator_service.create_video_creator(video.id, creator.id)

        return video


def _handle_video_extraction(params, video_meta, video_info):
    video = video_service.get_video_by_url(params.url)
    if params.subscribed and not video:
        video = _create_video(params, video_meta, video_info)
    return video


def _handle_download_task(video):
    try:
        task = task_service.create_task(video.id, video.url)
        message = message_service.create_message(task.to_dict())

        QueueManager.send_message(constants.QUEUE_VIDEO_DOWNLOAD, message.to_dict())

        logger.info(f"下载任务已发送: video_id={video.id}")

    except Exception as e:
        logger.error(f"发送下载任务失败: {e}", exc_info=True)


def _check_subscription_exist(subscription_id: int) -> bool:
    try:
        subscription = subscription_service.get_subscription_by_id(subscription_id)
        return subscription is not None and not subscription.is_deleted
    except Exception as e:
        logger.error(f"检查订阅存在性失败: subscription_id={subscription_id}, error={e}")
        return False



