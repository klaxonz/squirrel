import json
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Type
import threading

from PyCookieCloud import PyCookieCloud
from sqlalchemy import select, or_, and_
from sqlalchemy.sql.functions import count, func

from core import config
from core.config import settings
from core.database import get_session
from dto.subscription_dto import SubscriptionDto
from dto.video_dto import VideoExtractDto
from models.task.download_task import DownloadTask
from models.links import SubscriptionVideo
from models.subscription import Subscription
from models.task.task_state import TaskState
from services import download_service, subscription_service
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

            json_cookie_to_netscape(decrypted_data, expect_domains, config.get_cookies_file_path())
            json_cookie_to_netscape(decrypted_data, expect_domains, config.get_cookies_http_file_path())

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
                        and_(DownloadTask.status == TaskState.FAILED.value, DownloadTask.retry < 5),
                        (and_(DownloadTask.status.in_([TaskState.DOWNLOADING.value, TaskState.FAILED.value]),
                              DownloadTask.updated_at <= five_minutes_ago)))))
                for task in tasks:
                    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
                    downloading_tasks = session.scalars(
                        select(DownloadTask).where(DownloadTask.status == TaskState.DOWNLOADING.value,
                                                   DownloadTask.updated_at < ten_minutes_ago)).all()

                    if (task.status == TaskState.PENDING.value) and len(downloading_tasks) > 0:
                        continue

                    task.error_message = ''
                    task.status = TaskState.PENDING.value
                    task.retry = task.retry + 1
                    session.commit()

                    subscription_video = session.scalars(
                        select(SubscriptionVideo).where(SubscriptionVideo.video_id == task.video_id)).one()
                    if_subscribe = subscription_video is not None
                    # start(task.url, if_only_extract=False, if_subscribe=if_subscribe, if_retry=True)

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
                session.query(DownloadTask).filter(DownloadTask.status == TaskState.PENDING.value,
                                                   DownloadTask.retry >= 5).update({
                    DownloadTask.status: TaskState.FAILED.value
                })
                session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=10, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    _thread_pools = None
    _subscription_locks = {}

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
        cls.initialize_pools()

        subscription_ids = []
        with get_session() as session:
            subscriptions = session.scalars(
                select(Subscription).where(Subscription.is_deleted == 0))
            for subscription in subscriptions:
                subscription_ids.append(subscription.id)

        for subscription_id in subscription_ids:
            try:
                subscription = subscription_service.get_subscription_detail(subscription_id)
                pool = cls.get_pool(subscription.url)
                if pool:
                    pool.submit(cls.update_subscription_video, subscription)

            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    @classmethod
    def update_subscription_video(cls, subscription: SubscriptionDto):
        # Get or create lock for this subscription
        if subscription.id not in cls._subscription_locks:
            cls._subscription_locks[subscription.id] = threading.Lock()
        lock = cls._subscription_locks[subscription.id]

        # Try to acquire the lock, return if already locked
        if not lock.acquire(blocking=False):
            logger.info(f"Update already in progress for subscription {subscription.id}")
            return

        try:
            subscribe_channel = SubscriptionFactory.create_subscription(subscription.url)
            if subscription.total_videos == 0:
                is_extract_all = True
            elif subscription.total_videos - subscription.total_extract > settings.CHANNEL_UPDATE_DEFAULT_SIZE:
                is_extract_all = False
            else:
                is_extract_all = True
            video_list = subscribe_channel.get_subscribe_videos(extract_all=is_extract_all)
            if is_extract_all:
                with get_session() as session:
                    session.query(Subscription).filter(Subscription.id == subscription.id).update({
                        Subscription.total_videos: len(video_list)
                    })
                    session.commit()
            extract_video_list = video_list if is_extract_all else video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
            for video in extract_video_list:
                params = VideoExtractDto(
                    url=video,
                    subscribed=True,
                    only_extract=True,
                    subscription_id=subscription.id
                )
                download_service.start(params)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        finally:
            lock.release()

    @classmethod
    def shutdown(cls):
        if cls._thread_pools:
            for pool in cls._thread_pools.values():
                pool.shutdown(wait=True)
            cls._thread_pools = None
