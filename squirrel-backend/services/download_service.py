import datetime
import logging

from common import constants
from consumer import extract_task
from core.cache import RedisClient
from downloader.id_extractor import extract_id_from_url
from dto.video_dto import VideoExtractDto
from services import video_service, message_service
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger()
client = RedisClient.get_instance().client


def build_video_key(url: str):
    origin_video_id = extract_id_from_url(url)
    domain = extract_top_level_domain(url)
    return f'{constants.REDIS_KEY_VIDEO_EXTRACT_CACHE}:{domain}:{origin_video_id}'


def __check_video_exists(url: str) -> bool:
    """
    Check if video exists or is currently being extracted.
    
    Args:
        url: Video URL to check
        
    Returns:
        bool: True if video exists or is being extracted, False otherwise
    """
    if video_service.get_video_by_url(url):
        return True

    # Check if video is currently being extracted
    extract_key = build_video_key(url)
    extract_timestamp = client.hget(extract_key, constants.VIDEO_EXTRACT_FIELD_NAME)

    if not extract_timestamp:
        return False
    time_elapsed = datetime.datetime.now().timestamp() - float(extract_timestamp)
    is_extracting = time_elapsed < constants.VIDEO_EXTRACT_EXPIRE

    if is_extracting:
        logger.info(f"{url} is currently being extracted")

    return is_extracting


def start(params: VideoExtractDto):
    if params.only_extract:
        __check_video_exists(params.url)
    content = params.model_dump()
    message = message_service.create_message(content)
    extract_task.process_extract_message.send(message.to_dict())
