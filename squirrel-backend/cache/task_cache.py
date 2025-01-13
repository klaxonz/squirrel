import datetime

from common import constants
from core.cache import RedisClient
from downloader import id_extractor
from utils import url_helper

client = RedisClient.get_instance().client


def build_video_key(url: str):
    origin_video_id = id_extractor.extract_id_from_url(url)
    domain = url_helper.extract_top_level_domain(url)
    return f'{constants.REDIS_KEY_VIDEO_EXTRACT_CACHE}:{domain}:{origin_video_id}'


def get_extract_cache(url: str):
    key = build_video_key(url)
    return client.hget(key, constants.VIDEO_EXTRACT_FIELD_NAME)


def set_extract_cache(url: str, field_name: str):
    key = build_video_key(url)
    client.hset(key, field_name, datetime.datetime.now().timestamp())


def delete_extract_cache(url: str, field_name: str):
    key = build_video_key(url)
    client.hdel(key, field_name)
