import logging
import json

from common import constants
from mq.producer import RedisStreamProducer
from mq.duplicate_checker import create_simple_checker
from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service, message_service
from core.progress import progress_emitter, ProgressEvent, ProgressEventType

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
            
            # 发送完成事件，避免前端一直等待
            if params.subscription_id:
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_COMPLETE,
                    subscription_id=params.subscription_id,
                    video_id=video.id,
                    url=params.url,
                    message=f"视频已存在: {video.title}"
                ))
            return

    _send_to_extract_queue(params)


def _send_to_extract_queue(params: VideoExtractDto) -> None:
    content = params.model_dump()
    message = message_service.create_message(content)
    message_dict = message.to_dict()
    
    queue_name = constants.QUEUE_VIDEO_EXTRACT if params.is_manual else constants.QUEUE_VIDEO_EXTRACT_SCHEDULED
    
    # 对定时任务检查重复，手动触发不检查（允许用户强制重新提取）
    if not params.is_manual:
        checker = create_simple_checker(
            queue_name=queue_name,
            key_fn=lambda msg: json.loads(msg['body'])['url']
        )
        
        if checker.is_duplicate(message_dict):
            logger.debug(f"Video extraction task already in queue, skipping: {params.url}")
            
            # 发送完成事件，避免前端一直等待
            if params.subscription_id:
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.VIDEO_EXTRACTION_COMPLETE,
                    subscription_id=params.subscription_id,
                    url=params.url,
                    message="视频已在队列中，跳过重复提取"
                ))
            return
    
    RedisStreamProducer().send(queue_name, message_dict)


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


