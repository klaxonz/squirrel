import logging

from common import constants
from mq.producer import RedisStreamProducer
from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service, message_service

logger = logging.getLogger()


def enqueue_video_extraction(params: VideoExtractDto) -> None:
    """
    将视频提取任务加入队列
    注意：在批量调用时，订阅存在性检查应在外层完成，避免重复查询
    """
    if params.only_extract:
        video = video_service.get_video_by_url(params.url)
        if video:
            logger.debug(f"Video already extracted, skipping: {params.url}")
            return

    _send_to_extract_queue(params)


def _send_to_extract_queue(params: VideoExtractDto) -> None:
    content = params.model_dump()
    message = message_service.create_message(content)
    
    queue_name = constants.QUEUE_VIDEO_EXTRACT if params.is_manual else constants.QUEUE_VIDEO_EXTRACT_SCHEDULED
    RedisStreamProducer().send(queue_name, message.to_dict())


# 兼容旧代码的函数，标记为废弃
def start(params: VideoExtractDto) -> None:
    """
    @deprecated 请使用 enqueue_video_extraction
    此函数保留用于兼容性，将在未来版本移除
    """
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


