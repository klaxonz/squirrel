import logging
from datetime import datetime
from typing import Callable

import dramatiq

from common import constants
from common.constants import DOMAIN_QUEUE_MAPPING
from consumer import download_task
from core.database import get_session
from downloader.factory import DownloaderFactory
from dto.video_dto import VideoExtractDto
from meta.factory import VideoFactory
from models.message import Message
from services import video_service, task_service, message_service, subscription_video_service, creator_service, \
    video_creator_service
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger()


def create_processor(queue_name: str) -> Callable:
    actor_name = f"actor_{queue_name}"

    @dramatiq.actor(actor_name=actor_name, queue_name=queue_name)
    def processor(message):
        process_extract_task(message, queue_name)

    return processor


PROCESSORS = {
    domain: {
        'manual': create_processor(queues['manual']),
        'scheduled': create_processor(queues['scheduled']),
        'for_download': create_processor(queues['for_download'])
    }
    for domain, queues in DOMAIN_QUEUE_MAPPING.items()
}


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT)
def process_extract_message(message):
    _process_extract_message(message)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_SCHEDULED)
def process_extract_scheduled_message(message):
    _process_extract_message(message)


def _process_extract_message(message):
    url = None
    try:
        message_obj = Message.from_dict(message)
        params = VideoExtractDto.model_validate_json(message_obj.body)
        domain = extract_top_level_domain(params.url)
        if domain in PROCESSORS:
            processor_type = 'scheduled' if params.only_extract else 'for_download'
            processor = PROCESSORS[domain][processor_type]
            processor.send(message)
        else:
            logger.error(f"Unsupported domain: {domain}")

    except Exception as e:
        logger.error(
            f"处理消息时发生错误: {f'url:{url},' if url else ''} error: {e}",
            exc_info=True
        )


def process_extract_task(message, queue: str):
    try:
        logger.info(f"开始处理视频解析消息：{message}")
        message_obj = Message.from_dict(message)
        params = VideoExtractDto.model_validate_json(message_obj.body)
        video_info = _get_video_info(params.url, queue)
        if not video_info:
            return

        video_meta = VideoFactory.create_video(params.url, video_info)
        video = _handle_video_extraction(params, video_meta, video_info)
        if not params.only_extract:
            _handle_download_task(video)
    except Exception as e:
        logger.error(f"处理消息时发生错误: message: {message}, {e}", exc_info=True)


def _get_video_info(url, queue_name: str):
    downloader = DownloaderFactory.create_downloader(url)
    video_info = downloader.get_video_info(url, queue_name)
    if video_info is None or ('_type' in video_info and video_info['_type'] == 'playlist'):
        logger.info(f"{url} is not a valid video, skip")
        return None
    return video_info


def _create_video(params: VideoExtractDto, video_meta, video_info):
    with get_session():
        video = video_service.get_video_by_url(video_meta.url)
        if not video:
            video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
            video = video_service.create_video(video_meta.url, video_info['title'], video_info['publish_date'],
                                               video_info['thumbnail'], video_info['duration'])
        subscription_video = subscription_video_service.get_subscription_video(params.subscription_id, video.id)
        if not subscription_video:
            subscription_video_service.create_subscription_video(params.subscription_id, video.id)

        actors = video_meta.actors
        if len(actors) > 0:
            for actor_meta in actors:
                creator = creator_service.get_creator_by_url(actor_meta.url)
                if not creator:
                    creator = creator_service.create_creator(actor_meta.url, actor_meta.name, actor_meta.avatar)
                video_creator = video_creator_service.get_video_creator(video.id, creator.id)
                if not video_creator:
                    video_creator_service.create_video_creator(video.id, creator.id)

        return video


def _handle_video_extraction(params, video_meta, video_info):
    video = video_service.get_video_by_url(params.url)
    if params.subscribed and not video:
        video = _create_video(params, video_meta, video_info)
    return video


def _handle_download_task(video):
    task = task_service.create_task(video.id, video.url)
    message = message_service.create_message(task.to_dict())
    download_task.process_download_message.send(message.to_dict())
