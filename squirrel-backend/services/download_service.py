import logging
import json

from mq.direct_producer import direct_domain_producer
from mq.duplicate_checker import create_simple_checker
from mq.queue_config import get_queue_config, QueueType, QueueMode
from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service, message_service
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain
from utils.metrics import metrics

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
            metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_extracted"})
            return

    _send_to_extract_queue(params)


def _send_to_extract_queue(params: VideoExtractDto) -> None:
    content = params.model_dump()
    message = message_service.create_message(content)
    message_dict = message.to_dict()
    
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
        # 构建域队列名称用于去重检查
        domain = extract_top_level_domain(params.url)
        config = get_queue_config()
        site = config.get_site_by_domain(domain)
        
        if not site:
            logger.error(f"Unsupported domain: {domain}, url={params.url}")
            return
        
        mode_mapping = {"manual": QueueMode.MANUAL, "incr": QueueMode.INCREMENTAL, "full": QueueMode.FULL}
        queue_name = config.build_queue_name(QueueType.VIDEO_EXTRACT, site, mode_mapping[priority])
        
        checker = create_simple_checker(
            queue_name=queue_name,
            key_fn=lambda msg: json.loads(msg['body'])['url']
        )
        
        if checker.is_duplicate(message_dict):
            logger.debug(f"Video extraction task already in queue, skipping: {params.url}")
            metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_in_queue"})
            return
    
    # 使用新的直接域队列生产者
    try:
        direct_domain_producer.send_video_extract(message_dict, params.url, priority)
    except ValueError as e:
        logger.error(f"Failed to send video extract message: {e}, url={params.url}")


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


