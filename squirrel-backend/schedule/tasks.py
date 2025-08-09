import json
import logging
from datetime import datetime, timedelta
from typing import List, Type
from PyCookieCloud import PyCookieCloud
from sqlalchemy import select, or_, and_
from common import constants
from mq.producer import RedisStreamProducer
from core import config
from core.config import settings
from core.database import get_session
from models.links import SubscriptionVideo
from models.subscription import Subscription
from models.task.download_task import DownloadTask
from models.task.task_state import TaskState
from services import subscription_service
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


@TaskRegistry.register(interval=30, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    """
    Refactored: scheduler now only scans subscriptions and enqueues update messages.
    Concurrency and locking are handled by the update consumer.
    """

    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                subscriptions = session.scalars(
                    select(Subscription).where(Subscription.is_deleted == False).order_by(Subscription.id.desc())
                ).all()

            from services import message_service
            for sub in subscriptions:
                try:
                    sub_detail = subscription_service.get_subscription_by_id(sub.id)
                    content = {
                        "subscription_id": getattr(sub_detail, 'id', sub.id),
                        "url": getattr(sub_detail, 'url', ''),
                        "total_videos": getattr(sub_detail, 'total_videos', 0),
                        "total_extract": getattr(sub_detail, 'total_extract', 0),
                        "is_nsfw": getattr(sub_detail, 'is_nsfw', False),
                    }
                    message = message_service.create_message(content)
                    RedisStreamProducer().send(constants.QUEUE_SUBSCRIPTION_UPDATE, message.to_dict())
                except Exception as e:
                    logger.error(f"Failed to enqueue update for subscription {sub.id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"AutoUpdateChannelVideo.run unexpected error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        pass
