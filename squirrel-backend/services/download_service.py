import logging
import json

from common import constants
from mq.producer import RedisStreamProducer
from mq.duplicate_checker import create_simple_checker
from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service, message_service
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger()


def enqueue_video_extraction(params: VideoExtractDto) -> None:
    """
    将视频提取任务加入队列
    注意：在批量调用时，订阅存在性检查应在外层完成，避免重复查询
    """
    domain = extract_top_level_domain(params.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        logger.info(f"Skip enqueue video extraction for disabled site: domain={domain}, url={params.url}")
        return

    if params.only_extract:
        video = video_service.get_video_by_url(params.url)
        if video:
            logger.debug(f"Video already extracted, skipping: {params.url}")
            return

    _send_to_extract_queue(params)


def _send_to_extract_queue(params: VideoExtractDto) -> None:
    content = params.model_dump()
    message = message_service.create_message(content)
    message_dict = message.to_dict()
    
    # 队列优先级策略：
    # 1. 手动触发 -> manual（最高优先级）
    # 2. 增量更新 -> incremental（高优先级，快速响应新视频）
    # 3. 全量更新 -> full（低优先级，慢慢处理历史视频）
    if params.is_manual:
        queue_name = constants.QUEUE_VIDEO_EXTRACT
    elif params.is_extract_all:
        queue_name = constants.QUEUE_VIDEO_EXTRACT_FULL
    else:
        queue_name = constants.QUEUE_VIDEO_EXTRACT_INCREMENTAL
    
    # 对自动任务检查重复，手动触发不检查（允许用户强制重新提取）
    if not params.is_manual:
        checker = create_simple_checker(
            queue_name=queue_name,
            key_fn=lambda msg: json.loads(msg['body'])['url']
        )
        
        if checker.is_duplicate(message_dict):
            logger.debug(f"Video extraction task already in queue, skipping: {params.url}")
            return
    
    RedisStreamProducer().send(queue_name, message_dict)


# 兼容旧代码的函数，标记为废弃
def start(params: VideoExtractDto) -> None:
    """
    @deprecated 请使用 enqueue_video_extraction
    此函数保留用于兼容性，将在未来版本移除
    """
    domain = extract_top_level_domain(params.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        logger.info(f"Skip legacy start() for disabled site: domain={domain}, url={params.url}")
        return

    from services import subscription_service
    
    if params.only_extract:
        if video_service.get_video_by_url(params.url):
            logger.info(f"{params.url} is already extracted")
            return
    
    subscription = subscription_service.get_subscription_by_id(params.subscription_id)
    if not subscription or subscription.is_deleted:
        logger.info(f"subscription {params.subscription_id} is not exist")
        return

    _send_to_extract_queue(params)


