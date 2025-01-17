import datetime
import logging

from cache import task_cache
from common import constants
from consumer import extract_task
from core.cache import RedisClient
from dto.video_dto import VideoExtractDto
from services import video_service, message_service, subscription_service

logger = logging.getLogger()
client = RedisClient.get_instance().client


def __check_video_exists(url: str) -> bool:
    if video_service.get_video_by_url(url):
        return True


def __check_video_extracting(url: str):
    extract_timestamp = task_cache.get_extract_cache(url)
    if not extract_timestamp:
        return False
    time_elapsed = datetime.datetime.now().timestamp() - float(extract_timestamp)
    return time_elapsed < constants.VIDEO_EXTRACT_EXPIRE


def __check_subscription_exist(subscription_id: int):
    subscription = subscription_service.get_subscription_by_id(subscription_id)
    return subscription.is_deleted is False


def start(params: VideoExtractDto):
    if params.only_extract:
        if __check_video_exists(params.url):
            logger.info(f"{params.url} is already extracted")
            return
        if __check_video_extracting(params.url):
            logger.info(f"{params.url} is currently being extracted")
            return
    if not __check_subscription_exist(params.subscription_id):
        logger.info(f"subscription {params.subscription_id} is not exist")
        return
    content = params.model_dump()
    message = message_service.create_message(content)
    extract_task.process_extract_message.send(message.to_dict())
    task_cache.set_extract_cache(params.url, constants.VIDEO_EXTRACT_FIELD_NAME)

