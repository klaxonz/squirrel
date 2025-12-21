from typing import List, Tuple

from sqlalchemy import delete, func, select

from common import constants
from core.cache import redis_client
from core.database import get_session
from models.links import SubscriptionVideo
from models.subscription import Subscription
from models.task.download_task import DownloadTask
from models.task.task_state import TaskState
from models.video import Video
from services import download_service
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service


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
        session.execute(delete(DownloadTask).where(DownloadTask.id == task_id))
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
    if not tasks:
        return []

    task_data = []
    video_ids = [task.video_id for task in tasks]

    with get_session() as session:
        results = session.execute(
            select(Video, Subscription)
            .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
            .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
            .where(Video.id.in_(video_ids))
        ).all()

        video_map = {}
        video_subscription_map = {}
        for video, subscription in results:
            video_map[video.id] = video
            video_subscription_map[video.id] = subscription

        for task in tasks:
            video = video_map.get(task.video_id)
            subscription = video_subscription_map.get(task.video_id)
            if not video or not subscription:
                continue

            progress = redis_client.hgetall(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task.id}')
            task_data.append({
                "id": task.id,
                "thumbnail": thumbnail_downloader_service.get_thumbnail_url(video.id, video.thumbnail, video.url),
                "status": task.status,
                "title": video.title,
                "channel_name": subscription.name,
                "channel_avatar": subscription.avatar,
                "downloaded_size": int(progress.get('downloaded_size', 0)),
                "total_size": int(progress.get('total_size', 0)),
                "speed": progress.get('speed', ''),
                "eta": progress.get('eta', ''),
                "percent": progress.get('percent', ''),
                "error_message": task.error_message,
                "retry": task.retry,
                "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "created_at": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

    return task_data
