import json
import logging
from datetime import datetime
from typing import Callable

import dramatiq
from sqlalchemy import select

from common import constants
from common.constants import DOMAIN_QUEUE_MAPPING
from consumer import download_task
from core.cache import RedisClient
from core.config import settings
from core.database import get_session
from downloader.downloader import Downloader
from downloader.id_extractor import extract_id_from_url
from meta.factory import VideoFactory
from models.creator import Creator
from models.download_task import DownloadTask
from models.links import SubscriptionVideo, VideoCreator
from models.message import Message
from models.video import Video
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
        'scheduled': create_processor(queues['scheduled'])
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
        extract_info = _parse_message(message_obj)
        if_manual = extract_info['if_manual']
        url = extract_info['url']
        domain = extract_top_level_domain(url)

        # 获取对应的处理器
        if domain in PROCESSORS:
            processor_type = 'manual' if if_manual else 'scheduled'
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
        extract_info = _parse_message(message_obj)
        url, domain, video_id = _extract_video_info(extract_info['url'])

        if _should_skip_processing(url, extract_info):
            return

        video_info = _get_video_info(url, queue)
        if not video_info:
            return

        video_meta = _create_video(url, video_info)

        _handle_video_extraction(extract_info, video_meta, video_info)
        if not extract_info['if_only_extract']:
            _handle_download_task(extract_info, video_meta, video_id)
    except Exception as e:
        logger.error(f"处理消息时发生错误: message: {message}, {e}", exc_info=True)


def _parse_message(message):
    return json.loads(message.body)


def _extract_video_info(url):
    domain = extract_top_level_domain(url)
    video_id = extract_id_from_url(url)
    return url, domain, video_id


def _should_skip_processing(url, extract_info):
    video = _get_video(url)
    if extract_info['if_only_extract'] and video is not None:
        _update_redis_cache(video.id, 'if_extract')
        logger.debug(f"视频已解析：{video.url}, 跳过")
        return True
    return False


def _get_video_info(url, task_name):
    video_info = Downloader.get_video_info_thread(url, task_name)
    if video_info is None or ('_type' in video_info and video_info['_type'] == 'playlist'):
        logger.info(f"{url} is not a valid video, skip")
        return None
    return video_info


def _create_video(url, video_info):
    return VideoFactory.create_video(url, video_info)


def _get_video(url):
    with get_session() as session:
        video = session.scalars(select(Video).where(Video.id == url)).first()
        if video:
            session.expunge(video)
    return video


def _handle_video_extraction(extract_info, video_meta, video_info):
    if extract_info['if_subscribe'] and not _get_video(video_meta.url):
        _create_channel_video(video_meta, video_info, extract_info)


def _create_channel_video(video_meta, video_info, extract_info):
    with get_session() as session:
        logger.info(f"开始创建channel video: {video_meta.url}")

        # 创建video
        video = session.scalars(select(Video).where(Video.url == video_meta.url)).first()
        if not video:
            video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
            video = Video(
                title=video_info['title'],
                description=None,
                url=video_meta.url,
                duration=video_info['duration'],
                thumbnail=video_info['thumbnail'],
                publish_date=video_info['publish_date'],
                extra_data={}
            )
            session.add(video)
        subscription_video = session.scalars(select(SubscriptionVideo).where(
            SubscriptionVideo.subscription_id == extract_info['subscribe_id'],
            SubscriptionVideo.video_id == video.id)).first()
        if not subscription_video:
            subscription_video = SubscriptionVideo(
                subscription_id=extract_info['subscribe_id'],
                video_id=video.id
            )
            session.add(subscription_video)
        session.commit()

        actors = video_meta.actors
        if len(actors) > 0:
            for actor_meta in actors:
                creator = session.scalars(select(Creator).where(Creator.url == actor_meta.url)).first()
                if not creator:
                    creator = Creator(
                        name=actor_meta.name,
                        url=actor_meta.url,
                        avatar=actor_meta.avatar,
                        description=None,
                        extra_data={}
                    )
                    session.add(creator)
                video_creator = session.scalars(select(VideoCreator).where(
                    VideoCreator.video_id == video.id,
                    VideoCreator.creator_id == creator.id)).first()
                if not video_creator:
                    video_creator = VideoCreator(
                        video_id=video.id,
                        creator_id=creator.id
                    )
                    session.add(video_creator)
                session.commit()


def _handle_download_task(extract_info, video, video_id):
    if_manual = extract_info['if_manual']
    channel_video = _get_video(video.url)
    if extract_info['if_subscribe'] and channel_video and channel_video.if_downloaded:
        return

    logger.info(f"开始生成视频任务：channel {video.uploader.name}, video: {video.url}")
    task = _get_or_create_download_task(video, video_id)
    if _should_skip_download(extract_info, task):
        return

    _create_download_message(task, if_manual)
    logger.info(f"结束生成视频任务：channel {video.uploader.name}, video: {video.url}")


def _get_or_create_download_task(video, video_id):
    with get_session() as session:
        task = session.scalars(select(DownloadTask).where(DownloadTask.video_id == video_id)).first()
        if not task:
            task = _create_download_task(video, video_id, session)
        else:
            session.refresh(task)

        return task


def _create_download_task(video, video_id, session):
    task = DownloadTask()
    task.url = video.url
    task.video_id = video_id
    task.status = "PENDING"
    session.add(task)
    session.commit()
    return task


def _should_skip_download(extract_info, task):
    with get_session() as session:
        if task:
            task = session.merge(task)
        if task and not extract_info['if_manual_download'] and not extract_info['if_retry'] and not extract_info['if_manual_retry']:
            _update_redis_cache(task.video_id, 'if_download')
            logger.info(f"视频已生成任务：channel {task.channel_name}, video: {task.url}")
            return True
        if task and task.status == 'COMPLETED':
            logger.info(f"视频已下载：channel {task.channel_name}, video: {task.url}")
            return True
        if task and not extract_info['if_manual_retry'] and task.retry >= settings.DOWNLOAD_RETRY_THRESHOLD:
            logger.info(f"视频下载已超过重试次数：channel {task.channel_name}, video: {task.url}")
            return True
        return False


def _create_download_message(task, if_manual):
    with get_session() as session:
        task = session.merge(task)
        message = Message()
        message.body = task.model_dump_json()
        session.add(message)
        session.commit()

        message = session.scalars(select(Message).where(Message.id == message.id)).first()
        dump_json = message.model_dump_json()
        if if_manual:
            download_task.process_download_message.send(dump_json)
        else:
            download_task.process_download_scheduled_message.send(dump_json)
        message.send_status = 'SENDING'
        session.commit()


def _update_redis_cache(video_id, cache_key):
    key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{video_id}"
    RedisClient.get_instance().client.hset(key, cache_key, datetime.now().timestamp())
