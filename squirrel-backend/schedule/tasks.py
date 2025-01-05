import json
import logging
import re
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from logging import exception
from typing import List, Type

import feedparser
from PyCookieCloud import PyCookieCloud
from sqlalchemy import select, or_, and_
from sqlalchemy.sql.functions import count, func

from core.config import settings
from core.database import get_session
from models.download_task import DownloadTask
from models.links import SubscriptionVideo
from models.podcast import PodcastChannel, PodcastSubscription, PodcastEpisode
from models.subscription import Subscription
from services.download_service import start
from subscribe.factory import SubscriptionFactory
from utils.cookie import json_cookie_to_netscape

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
                tasks = session.scalars(select(DownloadTask).where(
                    or_(
                        and_(DownloadTask.status == 'FAILED', DownloadTask.retry < 5),
                        (and_(DownloadTask.status.in_(['DOWNLOADING', 'PENDING', 'WAITING']),
                              DownloadTask.updated_at <= five_minutes_ago)))))
                for task in tasks:
                    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
                    downloading_tasks = session.scalars(select(DownloadTask).where(DownloadTask.status == 'DOWNLOADING',
                                                                                DownloadTask.updated_at < ten_minutes_ago)).all()

                    if (task.status == 'PENDING' or task.status == 'WAITING') and len(downloading_tasks) > 0:
                        continue

                    task.error_message = ''
                    task.status = 'PENDING'
                    task.retry = task.retry + 1
                    session.commit()

                    subscription_video = session.scalars(
                        select(SubscriptionVideo).where(SubscriptionVideo.video_id == task.id)).one()
                    if_subscribe = subscription_video is not None
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
                tasks = session.scalars(
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

        subscription_ids = []
        with get_session() as outer_session:
            subscriptions = outer_session.scalars(select(Subscription).where(Subscription.is_enable == 1))
            for subscription in subscriptions:
                subscription_ids.append(subscription.id)

        for subscription_id in subscription_ids:
            try:
                with get_session() as inner_session:
                    subscription = inner_session.scalars(
                        select(Subscription).where(Subscription.id == subscription_id)).one()
                    pool = cls.get_pool(subscription.content_url)
                    if pool:
                        pool.submit(cls.update_subscription_video, subscription)

            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    @classmethod
    def update_subscription_video(cls, subscription):
        try:
            with get_session() as session:
                subscription = session.merge(subscription)
                logger.debug(f"update {subscription.content_name} subscription video start")
                subscribe_channel = SubscriptionFactory.create_subscription(subscription.content_url)

                # 下载全部的
                update_all = subscription.is_download_all or subscription.is_extract_all
                video_list = subscribe_channel.get_subscribe_videos(subscription=subscription, update_all=update_all)
                extract_video_list = []
                extract_download_video_list = []
                if subscription.is_extract_all:
                    if subscription.is_auto_download:
                        if subscription.is_download_all:
                            extract_download_video_list = video_list
                        else:
                            extract_video_list = video_list[settings.CHANNEL_UPDATE_DEFAULT_SIZE:]
                            extract_download_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
                    else:
                        extract_video_list = video_list

                else:
                    if subscription.is_auto_download:
                        extract_download_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
                    else:
                        extract_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]

                for video in extract_video_list:
                    start(video, if_subscribe=True, subscribe_id=subscription.id)
                for video in extract_download_video_list:
                    start(video, if_only_extract=False, if_subscribe=True, subscribe_id=subscription.id)
                logger.debug(f"update {subscription.content_name} video end")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        if cls._thread_pools:
            for pool in cls._thread_pools.values():
                pool.shutdown(wait=True)
            cls._thread_pools = None


@TaskRegistry.register(interval=30, unit='minutes')
class RepairChanelInfoForTotalVideos(BaseTask):
    @classmethod
    def run(cls):
        subscription_ids = []
        with get_session() as session:
            subscriptions = session.scalars(select(Subscription)).all()
            for subscription in subscriptions:
                subscription_ids.append(subscription.id)

        for subscription_id in subscription_ids:
            try:
                with get_session() as session:
                    subscription = session.scalars(
                        select(Subscription).where(Subscription.id == subscription_id)).first()
                    videos_count = session.scalars(select(count(SubscriptionVideo.video_id)).where(
                        SubscriptionVideo.subscription_id == subscription_id)).one()
                    if subscription.total_videos is not None and subscription.total_videos >= videos_count and subscription.total_videos > 0:
                        continue
                    subscribe_channel = SubscriptionFactory.create_subscription(subscription.content_url)
                    videos = subscribe_channel.get_subscribe_videos(subscription, update_all=True)
                    subscription.total_videos = len(videos)
                    session.commit()
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=1, unit='minutes')
class AutoUpdateSubscriptionExtractAll(BaseTask):
    @classmethod
    def run(cls):
        with get_session() as session:
            subscriptions = session.scalars(select(Subscription)).all()
            for subscription in subscriptions:
                extract_count = session.scalars(
                    select(func.count(SubscriptionVideo.video_id)).where(
                        SubscriptionVideo.subscription_id == subscription.id)).one()
                if subscription.total_videos is not None and subscription.total_videos > extract_count and subscription.total_videos - extract_count > 10:
                    subscription.is_extract_all = 1
                else:
                    subscription.is_extract_all = 0
                session.add(subscription)
                session.commit()
                session.refresh(subscription)


@TaskRegistry.register(interval=30, unit='minutes')
class UpdatePodcastsTask(BaseTask):
    @classmethod
    def run(cls):
        logger.info('开始更新播客内容')
        try:
            with get_session() as session:
                channels = session.scalars(
                    select(PodcastChannel)
                    .join(PodcastSubscription, PodcastSubscription.channel_id == PodcastChannel.id)
                ).all()

                for channel in channels:
                    try:
                        feed = feedparser.parse(channel.rss_url)
                        if hasattr(feed, 'bozo_exception'):
                            logger.error(f'解析播客RSS失败: {channel.title}, {feed.bozo_exception}')
                            continue

                        if hasattr(feed.feed, "description"):
                            channel.description = re.sub(r'<.*?>', '', feed.feed.description)
                        if hasattr(feed.feed, "image"):
                            channel.cover_url = feed.feed.image.href
                        channel.last_updated = datetime.now()
                        session.add(channel)

                        for entry in feed.entries:
                            # 检查剧集是否已存在
                            existing = session.scalars(
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
