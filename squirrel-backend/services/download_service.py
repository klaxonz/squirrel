import logging

from core.cache import redis_client
from queues.direct_producer import direct_domain_producer
from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service, message_service
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain
from utils.metrics import metrics

logger = logging.getLogger()


def enqueue_video_extraction(params: VideoExtractDto) -> bool:
    """
    将视频提取任务加入队列
    注意：在批量调用时，订阅存在性检查应在外层完成，避免重复查询
    """
    domain = extract_top_level_domain(params.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        logger.info(f"Skip enqueue video extraction for disabled site: domain={domain}, url={params.url}")
        return False

    if params.only_extract:
        video = video_service.get_video_by_url(params.url)
        if video:
            logger.debug(f"Video already extracted, skipping: {params.url}")
            metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_extracted"})
            return False

    return _send_to_extract_queue(params)


def _build_video_dedupe_key(url: str, priority: str) -> str:
    return f"dedupe:video_extract:{priority}:{url}"


def clear_video_extraction_dedupe(params: VideoExtractDto) -> None:
    if params.is_manual:
        return
    priority = "full" if params.is_extract_all else "incr"
    redis_client.delete(_build_video_dedupe_key(params.url, priority))


def _send_to_extract_queue(params: VideoExtractDto) -> bool:
    content = params.model_dump()
    message = message_service.create_message(content)
    message_dict = message.to_dict()
    dedupe_key = None
    
    # 队列优先级策略：
    # 1. 手动触发 -> manual（最高优先级）
    # 2. 增量更新 -> incr（高优先级，快速响应新视频）
    # 3. 全量更新 -> full（低优先级，慢慢处理历史视频）
    if params.is_manual:
        priority = "manual"
    elif params.is_extract_all:
        priority = "full"
    else:
        priority = "incr"
    
    # 对自动任务检查重复，手动触发不检查（允许用户强制重新提取）
    if not params.is_manual:
        domain = extract_top_level_domain(params.url)
        dedupe_key = _build_video_dedupe_key(params.url, priority)
        acquired = redis_client.set(dedupe_key, '1', nx=True, ex=600)
        if not acquired:
            logger.debug(f"Video extraction task already reserved, skipping: {params.url}")
            metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_in_queue"})
            return False
    
    try:
        direct_domain_producer.send_video_extract(message_dict, params.url, priority)
        return True
    except ValueError as e:
        if dedupe_key:
            redis_client.delete(dedupe_key)
        logger.error(f"Failed to send video extract message: {e}, url={params.url}")
        return False



