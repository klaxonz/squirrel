import datetime

from common import constants
from core.cache import RedisClient
from sites.id_extractor import IdExtractorFactory
from utils import url_helper

client = RedisClient.get_instance().client


def _extract_domain_and_id(url: str):
    id_extractor = IdExtractorFactory.get(url)
    origin_video_id = id_extractor.extract_id()
    domain = url_helper.extract_top_level_domain(url)
    return domain, origin_video_id


def build_video_key(url: str):
    domain, origin_video_id = _extract_domain_and_id(url)
    return f'{constants.REDIS_KEY_VIDEO_EXTRACT_CACHE}:{domain}:{origin_video_id}'


def get_extract_cache(url: str):
    key = build_video_key(url)
    ts = client.hget(key, constants.VIDEO_EXTRACT_FIELD_NAME)
    if not ts:
        return None
    try:
        tsf = float(ts)
    except Exception:
        # 非法时间戳，清理并视为不存在
        client.hdel(key, constants.VIDEO_EXTRACT_FIELD_NAME)
        return None
    now = datetime.datetime.now().timestamp()
    # 过期则清理并视为不存在，避免长时间卡住
    if now - tsf > constants.VIDEO_EXTRACT_EXPIRE:
        client.hdel(key, constants.VIDEO_EXTRACT_FIELD_NAME)
        return None
    return ts


def set_extract_cache(url: str, field_name: str):
    key = build_video_key(url)
    client.hset(key, field_name, datetime.datetime.now().timestamp())
    # 为键设置过期时间，避免异常情况下长期占用
    client.expire(key, constants.VIDEO_EXTRACT_EXPIRE)


def delete_extract_cache(url: str, field_name: str):
    key = build_video_key(url)
    client.hdel(key, field_name)

