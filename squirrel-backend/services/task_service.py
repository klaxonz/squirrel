from typing import List, Tuple

from sqlalchemy import func, select

from common import constants
from core.cache import RedisClient
from core.database import get_session
from models.links import SubscriptionVideo
from models.subscription import Subscription
from models.task.download_task import DownloadTask
from models.task.task_state import TaskState
from models.video import Video
from services import download_service


def create_task(video_id: int, url: str) -> DownloadTask:
    with get_session() as session:
        task = DownloadTask()
        task.url = url
        task.video_id = video_id
        task.status = TaskState.PENDING.value
        session.add(task)
        session.commit()
        return task


def get_task_by_id(task_id: int) -> DownloadTask:
    with get_session() as session:
        task = session.scalars(select(DownloadTask).where(DownloadTask.id == task_id)).first()
        return task


def update_task_status(task_id: int, new_state: TaskState):
    with get_session() as session:
        download_task = session.get(DownloadTask, task_id)
        download_task.transition_to(new_state.value)
        session.commit()


def start_download(url: str):
    download_service.start(url, if_only_extract=False, if_manual_download=True)


def retry_download(task_id: int):
    with get_session() as session:
        task = session.execute(select(DownloadTask).where(DownloadTask.id == task_id)).first()
        if task:
            task.status = 'PENDING'
            task.retry = task.retry + 1
            session.commit()
            download_service.start(task.url, if_only_extract=False, if_retry=True, if_manual_retry=True)


def pause_download(task_id: int):
    with get_session() as session:
        task = session.scalars(select(DownloadTask).where(DownloadTask.id == task_id)).first()
        if task:
            task.status = 'PAUSED'
            session.commit()
            download_service.stop(task.task_id)


def delete_task(task_id: int):
    with get_session() as session:
        session.query(DownloadTask).filter(DownloadTask.id == task_id).delete()
        session.commit()


def list_tasks(status: str, page: int, page_size: int) -> Tuple[List[dict], int]:
    with get_session() as session:
        base_query = select(DownloadTask)
        count_query = select(func.count(DownloadTask.id))
        if status:
            base_query = base_query.where(DownloadTask.status == status)
            count_query = count_query.where(DownloadTask.status == status)
        total_tasks = session.scalars(count_query).one()
        offset = (page - 1) * page_size

        base_query = base_query.order_by(DownloadTask.created_at.desc()).offset(offset).limit(page_size)
        tasks = session.scalars(base_query).all()

        task_convert_list = generate_task_data(tasks)

        return task_convert_list, total_tasks


def generate_task_data(tasks: List[DownloadTask]):
    client = RedisClient.get_instance().client
    task_data = []

    with get_session() as session:
        if tasks:
            video_ids = []
            for task in tasks:
                video_ids.append(task.video_id)
            videos = session.scalars(select(Video).where(Video.id.in_(video_ids))).all()
            videos_map = {}
            for video in videos:
                videos_map[video.id] = video

            subscription_videos = session.scalars(
                select(SubscriptionVideo).where(SubscriptionVideo.video_id.in_(video_ids))).all()
            subscription_ids = []
            subscription_maps = {}
            video_subscription_map = {}
            for subscription_video in subscription_videos:
                subscription_ids.append(subscription_video.subscription_id)

            if len(subscription_ids) > 0:
                subscriptions = session.scalars(select(Subscription).where(Subscription.id.in_(subscription_ids)))
                for subscription in subscriptions:
                    subscription_maps[subscription.id] = subscription
            for subscription_video in subscription_videos:
                video_subscription_map[subscription_video.video_id] = subscription_maps[
                    subscription_video.subscription_id]

            for task in tasks:
                progress = client.hgetall(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task.id}')
                downloaded_size = int(progress.get('downloaded_size', 0))
                total_size = int(progress.get('total_size', 0))
                speed = progress.get('speed', '')
                eta = progress.get('eta', '')
                percent = progress.get('percent', '')

                task_data.append({
                    "id": task.id,
                    "thumbnail": videos_map[task.video_id].thumbnail,
                    "status": task.status,
                    "title": videos_map[task.video_id].title,
                    "channel_name": video_subscription_map[task.video_id].name,
                    "channel_avatar": video_subscription_map[task.video_id].avatar,
                    "downloaded_size": downloaded_size,
                    "total_size": total_size,
                    "speed": speed,
                    "eta": eta,
                    "percent": percent,
                    "error_message": task.error_message,
                    "retry": task.retry,
                    "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "created_at": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                })

    return task_data
