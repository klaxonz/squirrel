import logging

from cache import task_cache
from common import constants
from core.cache import RedisClient
from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service, message_service, subscription_service
from mq.producer import RedisStreamProducer
from core.config import settings

logger = logging.getLogger()
client = RedisClient.get_instance().client


def __check_video_exists(url: str) -> bool:
    if video_service.get_video_by_url(url):
        return True
    return False


def __check_video_extracting(url: str):
    extract_timestamp = task_cache.get_extract_cache(url)
    return extract_timestamp is not None


def __check_subscription_exist(subscription_id: int):
    subscription = subscription_service.get_subscription_by_id(subscription_id)
    return subscription is not None and subscription.is_deleted is False


def start(params: VideoExtractDto):
    if params.only_extract:
        if __check_video_exists(params.url):
            logger.debug(f"{params.url} is already extracted")
            return
        # Per-video enqueued guard (48h TTL)
        if task_cache.is_video_enqueued(params.url):
            logger.debug(f"{params.url} is already enqueued for extract")
            return
        if __check_video_extracting(params.url):
            logger.debug(f"{params.url} is currently being extracted")
            return
    if not __check_subscription_exist(params.subscription_id):
        logger.info(f"subscription {params.subscription_id} is not exist")
        return

    # Set video enqueued flag before enqueue
    if params.only_extract:
        if not task_cache.set_video_enqueued(params.url, settings.VIDEO_EXTRACT_ENQUEUED_TTL_SECONDS):
            logger.debug(f"{params.url} enqueue race detected, skip")
            return

    content = params.model_dump()
    message = message_service.create_message(content)
    if params.is_manual:
        RedisStreamProducer().send(constants.QUEUE_VIDEO_EXTRACT, message.to_dict())
    else:
        RedisStreamProducer().send(constants.QUEUE_VIDEO_EXTRACT_SCHEDULED, message.to_dict())

    # Keep legacy extracting cache to avoid duplicate processing counts
    task_cache.set_extract_cache(params.url, constants.VIDEO_EXTRACT_FIELD_NAME)

