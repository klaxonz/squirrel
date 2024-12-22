import json
import logging
from datetime import datetime

import dramatiq
from sqlmodel import select

from common import constants
from consumer import download_task
from core.cache import RedisClient
from core.config import settings
from core.database import get_session
from downloader.downloader import Downloader
from downloader.id_extractor import extract_id_from_url
from meta.factory import VideoFactory
from models import Video, SubscriptionVideo, VideoCreator, Creator
from models.download_task import DownloadTask
from models.message import Message
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger()


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_TASK)
def process_extract_message(message):
    _process_extract_message(message)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_SCHEDULED_TASK)
def process_extract_scheduled_message(message):
    _process_extract_message(message)


def _process_extract_message(message: str):
    url = None
    try:
        message_obj = Message.model_validate(json.loads(message))
        extract_info = _parse_message(message_obj)
        if_manual = extract_info['if_manual']
        url = extract_info['url']
        domain = extract_top_level_domain(url)

        if if_manual:
            if domain == 'bilibili.com':
                process_extract_bilibili_message.send(message)
            elif domain == 'youtube.com':
                process_extract_youtube_message.send(message)
            elif domain == 'pornhub.com':
                process_extract_pornhub_message.send(message)
            elif domain == 'javdb.com':
                process_extract_javdb_message.send(message)
        else:
            if domain == 'bilibili.com':
                process_extract_bilibili_scheduled_message.send(message)
            elif domain == 'youtube.com':
                process_extract_youtube_scheduled_message.send(message)
            elif domain == 'pornhub.com':
                process_extract_pornhub_scheduled_message.send(message)
            elif domain == 'javdb.com':
                process_extract_javdb_scheduled_message.send(message)

    except Exception as e:
        if url:
            logger.error(f"处理消息时发生错误: url:{url}, error: {e}", exc_info=True)
        else:
            logger.error(f"处理消息时发生错误: {e}", exc_info=True)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_BILIBILI_TASK)
def process_extract_bilibili_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_BILIBILI_TASK)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_BILIBILI_SCHEDULED_TASK)
def process_extract_bilibili_scheduled_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_BILIBILI_SCHEDULED_TASK)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_YOUTUBE_TASK)
def process_extract_youtube_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_YOUTUBE_TASK)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_YOUTUBE_SCHEDULED_TASK)
def process_extract_youtube_scheduled_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_YOUTUBE_SCHEDULED_TASK)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_PORNHUB_TASK)
def process_extract_pornhub_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_PORNHUB_TASK)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_PORNHUB_SCHEDULED_TASK)
def process_extract_pornhub_scheduled_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_PORNHUB_SCHEDULED_TASK)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_JAVDB_TASK)
def process_extract_javdb_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_JAVDB_TASK)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_EXTRACT_JAVDB_SCHEDULED_TASK)
def process_extract_javdb_scheduled_message(message: str):
    process_extract_task(message, constants.QUEUE_VIDEO_EXTRACT_JAVDB_SCHEDULED_TASK)


def process_extract_task(message: str, queue: str):
    try:
        logger.info(f"开始处理视频解析消息：{message}")
        message_obj = Message.model_validate(json.loads(message))
        extract_info = _parse_message(message_obj)
        url, domain, video_id = _extract_video_info(extract_info['url'])

        if _should_skip_processing(url, domain, extract_info):
            return

        video_info = _get_video_info(url, queue)
        if not video_info:
            return

        video_meta = _create_video(url, video_info)

        _handle_video_extraction(extract_info, video_meta, video_info)
        if not extract_info['if_only_extract']:
            _handle_download_task(extract_info, video_meta, domain, video_id)
    except Exception as e:
        logger.error(f"处理消息时发生错误: message: {message}, {e}", exc_info=True)


def _parse_message(message):
    return json.loads(message.body)


def _extract_video_info(url):
    domain = extract_top_level_domain(url)
    video_id = extract_id_from_url(url)
    return url, domain, video_id


def _should_skip_processing(url, domain, extract_info):
    video = _get_video(url)
    if extract_info['if_only_extract'] and video is not None:
        _update_redis_cache(domain, video.id, 'if_extract')
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
        video = session.exec(select(Video).where(Video.video_id == url)).first()
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
        video = session.exec(select(Video).where(Video.video_url == video_meta.url)).first()
        if not video:
            # 时间戳转datetime
            video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
            video = Video(
                video_title=video_info['title'],
                video_description=None,
                video_url=video_meta.url,
                video_duration=video_info['duration'],
                thumbnail_url=video_info['thumbnail'],
                publish_date=video_info['publish_date'],
                extra_data={}
            )
            session.add(video)
        subscription_video = session.exec(select(SubscriptionVideo).where(
            SubscriptionVideo.subscription_id == extract_info['subscribe_id'],
            SubscriptionVideo.video_id == video.video_id)).first()
        if not subscription_video:
            subscription_video = SubscriptionVideo(
                subscription_id = extract_info['subscribe_id'],
                video_id = video.video_id
            )
            session.add(subscription_video)
        session.commit()

        actors = video_meta.actors
        if len(actors) > 0:
            for actor_meta in actors:
                creator = session.exec(select(Creator).where(Creator.creator_url == actor_meta.url)).first()
                if not creator:
                    creator = Creator(
                        creator_name=actor_meta.name,
                        creator_url=actor_meta.url,
                        avatar_url=actor_meta.avatar,
                        creator_description=None,
                        extra_data={}
                    )
                    session.add(creator)
                video_creator = session.exec(select(VideoCreator).where(
                    VideoCreator.video_id == video.video_id,
                                    VideoCreator.creator_id == creator.creator_id)).first()
                if not video_creator:
                    video_creator = VideoCreator(
                        video_id=video.video_id,
                        creator_id=creator.creator_id
                    )
                    session.add(video_creator)
                session.commit()



def _handle_download_task(extract_info, video, domain, video_id):
    if_manual = extract_info['if_manual']
    channel_video = _get_video(video.url)
    if extract_info['if_subscribe'] and channel_video and channel_video.if_downloaded:
        return

    logger.info(f"开始生成视频任务：channel {video.uploader.name}, video: {video.url}")
    task = _get_or_create_download_task(video, domain, video_id)
    if _should_skip_download(extract_info, task):
        return

    _create_download_message(task, if_manual)
    logger.info(f"结束生成视频任务：channel {video.uploader.name}, video: {video.url}")


def _get_or_create_download_task(video, domain, video_id):
    with get_session() as session:
        task = session.exec(select(DownloadTask).where(
            DownloadTask.domain == domain,
            DownloadTask.video_id == video_id
        )).first()
        if not task:
            task = _create_download_task(video, domain, video_id, session)
        else:
            session.refresh(task)
        
        return task


def _create_download_task(video, domain, video_id, session):
    uploader = video.uploader
    task = DownloadTask()
    task.url = video.url
    task.domain = domain
    task.title = video.title
    task.thumbnail = video.thumbnail
    task.video_id = video_id
    task.status = "PENDING"
    task.channel_id = uploader.id
    task.channel_url = uploader.url
    task.channel_name = uploader.name
    task.channel_avatar = uploader.avatar
    session.add(task)
    session.commit()
    return task


def _should_skip_download(extract_info, task):
    with get_session() as session:
        if task:
            task = session.merge(task)
        if task and not extract_info['if_manual_download'] and not extract_info['if_retry'] and not extract_info['if_manual_retry']:
            _update_redis_cache(task.domain, task.video_id, 'if_download')
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

        message = session.exec(select(Message).where(Message.message_id == message.message_id)).first()
        dump_json = message.model_dump_json()
        if if_manual:
            download_task.process_download_message.send(dump_json)
        else:
            download_task.process_download_scheduled_message.send(dump_json)
        message.send_status = 'SENDING'
        session.commit()


def _update_redis_cache(domain, video_id, cache_key):
    key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{domain}:{video_id}"
    RedisClient.get_instance().client.hset(key, cache_key, datetime.now().timestamp())


