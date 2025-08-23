import json
import logging
from datetime import timedelta, datetime
from sqlalchemy import select, and_, or_
from core.database import get_session
from models.links import SubscriptionVideo
from models.task.download_task import DownloadTask
from models.task.task_state import TaskState
from schedule.task import TaskRegistry, BaseTask


logger = logging.getLogger(__name__)


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

