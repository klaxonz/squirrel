import logging

from common import constants
from core.cache import RedisClient
from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service, message_service, subscription_service
from mq.producer import RedisStreamProducer

logger = logging.getLogger()
client = RedisClient.get_instance().client


def __check_video_exists(url: str) -> bool:
    if video_service.get_video_by_url(url):
        return True
    return False


def __check_subscription_exist(subscription_id: int):
    subscription = subscription_service.get_subscription_by_id(subscription_id)
    return subscription is not None and subscription.is_deleted is False


def start(params: VideoExtractDto):
    if params.only_extract:
        if __check_video_exists(params.url):
            logger.debug(f"{params.url} is already extracted")
            return
    if not __check_subscription_exist(params.subscription_id):
        logger.info(f"subscription {params.subscription_id} is not exist")
        return

    content = params.model_dump()
    message = message_service.create_message(content)
    if params.is_manual:
        RedisStreamProducer().send(constants.QUEUE_VIDEO_EXTRACT, message.to_dict())
    else:
        RedisStreamProducer().send(constants.QUEUE_VIDEO_EXTRACT_SCHEDULED, message.to_dict())


