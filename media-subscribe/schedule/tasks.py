import json
import logging
import random
import re
import time
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Type

import feedparser
from PyCookieCloud import PyCookieCloud
from sqlmodel import col, or_, and_, select, func

from common import constants
from core.cache import RedisClient
from meta import VideoFactory
from model.podcast import PodcastChannel, PodcastSubscription, PodcastEpisode
from services.channel_service import ChannelService
from subscribe.factory import SubscribeChannelFactory
from utils.cookie import json_cookie_to_netscape
from core.database import get_session
from core.config import settings
from downloader.downloader import Downloader
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask
from services.download_service import start

logger = logging.getLogger()


class BaseTask:
    interval: int = 60  # Default interval in seconds
    unit: str = 'seconds'
    start_immediately: bool = True

    @classmethod
    def run(cls):
        raise NotImplementedError("Subclasses must implement run method")


class TaskRegistry:
    tasks: List[Type[BaseTask]] = []

    @classmethod
    def register(cls, interval: int, unit: str = 'seconds', start_immediately: bool = True):
        def decorator(task_class):
            task_class.interval = interval
            task_class.unit = unit
            task_class.start_immediately = start_immediately
            cls.tasks.append(task_class)
            return task_class

        return decorator


@TaskRegistry.register(interval=60, unit='minutes')
class SyncCookies(BaseTask):
    @classmethod
    def run(cls):
        try:
            cookie_cloud = PyCookieCloud(settings.COOKIE_CLOUD_URL, settings.COOKIE_CLOUD_UUID,
                                         settings.COOKIE_CLOUD_PASSWORD)
            the_key = cookie_cloud.get_the_key()
            if not the_key:
                logger.info('Failed to get the key')
                return
            encrypted_data = cookie_cloud.get_encrypted_data()
            if not encrypted_data:
                logger.info('Failed to get encrypted data')
                return
            decrypted_data = cookie_cloud.get_decrypted_data()
            if not decrypted_data:
                logger.info('Failed to get decrypted data')
                return
            domains = settings.COOKIE_CLOUD_DOMAIN
            if domains:
                expect_domains = domains.split(',')
            else:
                expect_domains = []

            json_cookie_to_netscape(decrypted_data, expect_domains, settings.get_cookies_file_path())
            json_cookie_to_netscape(decrypted_data, expect_domains, settings.get_cookies_http_file_path())

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=1, unit='minutes')
class RetryFailedTask(BaseTask):
    @classmethod
    def run(cls):
        try:
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            with get_session() as session:
                tasks = session.exec(select(DownloadTask).where(
                    or_(
                        and_(DownloadTask.status == 'FAILED', DownloadTask.retry < 5),
                        (and_(col(DownloadTask.status).in_(['DOWNLOADING', 'PENDING', 'WAITING']),
                              DownloadTask.updated_at <= five_minutes_ago)))))
                for task in tasks:
                    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
                    downloading_tasks = session.exec(select(DownloadTask).where(DownloadTask.status == 'DOWNLOADING',
                                                                                DownloadTask.updated_at < ten_minutes_ago)).all()

                    if (task.status == 'PENDING' or task.status == 'WAITING') and len(downloading_tasks) > 0:
                        continue

                    task.error_message = ''
                    task.status = 'PENDING'
                    task.retry = task.retry + 1
                    session.commit()

                    channel = session.exec(select(Channel).where(Channel.channel_id == task.channel_id)).one()
                    if_subscribe = channel is not None
                    start(task.url, if_only_extract=False, if_subscribe=if_subscribe, if_retry=True)

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=1, unit='minutes')
class ChangeStatusTask(BaseTask):
    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                tasks = session.exec(
                    select(DownloadTask).where(DownloadTask.status == 'PENDING', DownloadTask.retry >= 5))
                for task in tasks:
                    task.status = 'FAILED'
                    session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=10, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    _thread_pools = None

    @classmethod
    def initialize_pools(cls):
        if cls._thread_pools is None:
            cls._thread_pools = {
                'bilibili': ThreadPoolExecutor(max_workers=1, thread_name_prefix='bilibili'),
                'pornhub': ThreadPoolExecutor(max_workers=1, thread_name_prefix='pornhub'),
                'youtube': ThreadPoolExecutor(max_workers=1, thread_name_prefix='youtube'),
                'javdb': ThreadPoolExecutor(max_workers=1, thread_name_prefix='javdb')
            }

    @classmethod
    def get_pool(cls, url):
        if cls._thread_pools is None:
            cls.initialize_pools()
        
        if 'bilibili' in url:
            return cls._thread_pools['bilibili']
        elif 'pornhub' in url:
            return cls._thread_pools['pornhub']
        elif 'youtube' in url:
            return cls._thread_pools['youtube']
        elif 'javdb' in url:
            return cls._thread_pools['javdb']
        return None

    @classmethod
    def run(cls):
        logger.info('auto_update_channel_video start')
        cls.initialize_pools()
        
        channel_ids = []
        with get_session() as outer_session:
            channels = outer_session.exec(select(Channel).where(Channel.if_enable == 1))
            for channel in channels:
                channel_ids.append(channel.channel_id)

        for channel_id in channel_ids:
            try:
                with get_session() as inner_session:
                    channel = inner_session.exec(select(Channel).where(Channel.channel_id == channel_id)).one()
                    pool = cls.get_pool(channel.url)
                    if pool:
                        pool.submit(cls.update_channel_video, channel)
                    
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    @classmethod
    def update_channel_video(cls, channel):
        redis_client = RedisClient.get_instance().client

        # Check if the channel is in the unsubscribed set
        if redis_client.sismember(constants.UNSUBSCRIBED_CHANNELS_SET, channel.channel_id):
            logger.info(f"Skipping update for recently unsubscribed channel: {channel.name}")
            return

        logger.debug(f"update {channel.name} channel video start")
        subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(channel.url)
        if channel.avatar is None:
            with get_session() as session:
                channel = session.exec(select(Channel).where(Channel.channel_id == channel.channel_id)).one()
                channel.avatar = subscribe_channel.get_channel_info().avatar
                session.commit()
        # 下载全部的
        update_all = channel.if_download_all or channel.if_extract_all
        video_list = subscribe_channel.get_channel_videos(channel=channel, update_all=update_all)
        extract_video_list = []
        extract_download_video_list = []
        if channel.if_extract_all:
            if channel.if_auto_download:
                if channel.if_download_all:
                    extract_download_video_list = video_list
                else:
                    extract_video_list = video_list[settings.CHANNEL_UPDATE_DEFAULT_SIZE:]
                    extract_download_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
            else:
                extract_video_list = video_list

        else:
            if channel.if_auto_download:
                extract_download_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
            else:
                extract_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]

        for video in extract_video_list:
            start(video, if_subscribe=True)
        for video in extract_download_video_list:
            start(video, if_only_extract=False, if_subscribe=True)
        logger.debug(f"update {channel.name} channel video end")

    @classmethod
    def shutdown(cls):
        if cls._thread_pools:
            for pool in cls._thread_pools.values():
                pool.shutdown(wait=True)
            cls._thread_pools = None


@TaskRegistry.register(interval=60, unit='minutes')
class RepairDownloadTaskInfo(BaseTask):
    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                download_tasks = session.exec(select(DownloadTask).where(col(DownloadTask.channel_name).is_(None)))
                for download_task in download_tasks:
                    if download_task.channel_name is not None:
                        continue

                    base_info = Downloader.get_video_info(download_task.url)
                    video = VideoFactory.create_video(download_task.url, base_info)
                    download_task.channel_id = video.uploader.id
                    download_task.channel_url = video.uploader.url
                    download_task.channel_name = video.uploader.name
                    download_task.channel_avatar = video.uploader.avatar
                    session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=30, unit='minutes')
class RepairChanelInfoForTotalVideos(BaseTask):
    @classmethod
    def run(cls):
        channel_ids = []
        with get_session() as session:
            channel_service = ChannelService()
            channels = session.exec(select(Channel)).all()
            for channel in channels:
                channel_ids.append(channel.channel_id)

        for channel_id in channel_ids:
            try:
                with get_session() as session:
                    channel = session.exec(select(Channel).where(Channel.channel_id == channel_id)).one()
                    extract_videos = channel_service.count_channel_videos(channel.channel_id)
                    if channel.total_videos >= extract_videos and channel.total_videos > 0:
                        continue
                    subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(channel.url)
                    videos = subscribe_channel.get_channel_videos(channel, update_all=True)
                    channel.total_videos = len(videos)
                    session.commit()
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=120, unit='minutes')
class RepairChannelVideoDuration(BaseTask):
    @classmethod
    def run(cls):
        url = ''
        with get_session() as session:
            statement = select(ChannelVideo).where(ChannelVideo.duration is None).order_by(
                col(ChannelVideo.created_at).desc())
            channel_videos = session.exec(statement)
            for channel_video in channel_videos:
                try:
                    if channel_video.duration is not None:
                        continue
                    url = channel_video.url
                    video = VideoFactory.create_video(url, None)
                    if not video.video_exists():
                        logger.info(f"video not exists: {url}")
                        continue

                    base_info = Downloader.get_video_info(url)
                    video = VideoFactory.create_video(url, base_info)
                    time.sleep(random.randint(1, 2))

                    if base_info is None or video.duration is None:
                        continue
                    channel_video.duration = video.duration
                    session.commit()
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"An unexpected error occurred: url: {url}, {e}", url, exc_info=True)


@TaskRegistry.register(interval=1, unit='minutes')
class AutoUpdateChannelExtractAll(BaseTask):
    @classmethod
    def run(cls):
        with get_session() as session:
            channels = session.exec(select(Channel)).all()
            for channel in channels:
                extract_count = session.exec(
                    select(func.count(col(ChannelVideo.id))).where(
                        ChannelVideo.channel_id == channel.channel_id)).one()
                if channel.total_videos > extract_count and channel.total_videos - extract_count > 10:
                    channel.if_extract_all = 1
                else:
                    channel.if_extract_all = 0
                session.add(channel)
                session.commit()
                session.refresh(channel)


@TaskRegistry.register(interval=30, unit='minutes')
class UpdatePodcastsTask(BaseTask):
    @classmethod
    def run(cls):
        """定时更新所有订阅的播客内容"""
        logger.info('开始更新播客内容')
        try:
            with get_session() as session:
                # 获取所有已订阅的播客
                channels = session.exec(
                    select(PodcastChannel)
                    .join(PodcastSubscription)
                ).all()

                for channel in channels:
                    try:
                        # 解析RSS feed
                        feed = feedparser.parse(channel.rss_url)
                        if hasattr(feed, 'bozo_exception'):
                            logger.error(f'解析播客RSS失败: {channel.title}, {feed.bozo_exception}')
                            continue

                        # 更新频道信息
                        if hasattr(feed.feed, "description"):
                            channel.description = re.sub(r'<.*?>', '', feed.feed.description)
                        if hasattr(feed.feed, "image"):
                            channel.cover_url = feed.feed.image.href
                        channel.last_updated = datetime.now()
                        session.add(channel)

                        # 添加新剧集
                        for entry in feed.entries:
                            # 检查剧集是否已存在
                            existing = session.exec(
                                select(PodcastEpisode)
                                .where(
                                    and_(
                                        PodcastEpisode.channel_id == channel.id,
                                        PodcastEpisode.title == entry.title
                                    )
                                )
                            ).first()
                            
                            if existing:
                                continue

                            description = entry.description if hasattr(entry, "description") else None
                            if description:
                                description = re.sub(r'<.*?>', '', description)
                            
                            episode = PodcastEpisode(
                                channel_id=channel.id,
                                title=entry.title,
                                description=description,
                                audio_url=entry.enclosures[0].href if hasattr(entry, "enclosures") else None,
                                published_at=datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") else None,
                                duration=cls.parse_duration(entry.itunes_duration) if hasattr(entry, "itunes_duration") else None
                            )
                            session.add(episode)

                        session.commit()
                        logger.info(f'更新播客成功: {channel.title}')

                    except Exception as e:
                        logger.error(f'更新播客失败: {channel.title}, {str(e)}', exc_info=True)
                        continue

        except Exception as e:
            logger.error(f'更新播客任务失败: {str(e)}', exc_info=True)


    @classmethod
    def parse_duration(cls, duration_str):
        parts = duration_str.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        elif len(parts) == 1:
            s = int(parts[0])
            return s
        else:
            return 0
