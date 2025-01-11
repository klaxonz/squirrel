from typing import List, Tuple

from sqlalchemy import func, select

from common import constants
from core.cache import RedisClient
from core.database import get_session
from models.download_task import DownloadTask
from models.video import Video
from services import download_service


def create_task(video_id: int, url: str) -> DownloadTask:
    with get_session() as session:
        task = DownloadTask()
        task.url = url
        task.video_id = video_id
        task.status = 'PENDING'
        session.add(task)
        session.commit()
        return task


def get_task_by_id(task_id: int) -> DownloadTask:
    with get_session() as session:
        task = session.scalars(select(DownloadTask).where(DownloadTask.id == task_id)).first()
        return task


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


def delete_download(task_id: int):
    with get_session() as session:
        task = session.scalars(select(DownloadTask).where(DownloadTask.id == task_id)).first()
        if task:
            session.delete(task)
            session.commit()
            download_service.stop(task.task_id)
            return True
        return False


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
        video_ids = []
        video_map = {}
        for task in tasks:
            video_ids.append(task.video_id)
        if len(video_ids) > 0:
            videos = session.scalars(select(Video).where(DownloadTask.video_id.in_(video_ids))).all()
            for video in videos:
                video_map[video.id] = video

        client = RedisClient.get_instance().client
        task_convert_list = []
        for task in tasks:
            task_id = task.id
            downloaded_size = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}',
                                          'downloaded_size')
            total_size = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'total_size')
            speed = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'speed')
            eta = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'eta')
            percent = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'percent')

            task_convert_list.append({
                "id": task.id,
                "title": video_map[task.video_id].title if video_map.get(task.video_id) else '',
                "thumbnail": video_map[task.video_id].thumbnail if video_map.get(task.video_id) else '',
                "status": task.status,
                "downloaded_size": int(downloaded_size) if downloaded_size else 0,
                "total_size": int(total_size) if total_size else 0,
                "speed": speed or '未知',
                "eta": eta or '未知',
                "percent": percent or '未知',
                "error_message": task.error_message,
                "retry": task.retry,
                "updated_at": task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "created_at": task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        return task_convert_list, total_tasks
