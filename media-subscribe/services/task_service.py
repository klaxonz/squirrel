from typing import List, Tuple

from sqlalchemy import func
from sqlmodel import select, col

from common import constants
from core.cache import RedisClient
from core.database import get_session
from model.download_task import DownloadTask
from services import download_service


class TaskService:
    def __init__(self):
        pass

    def start_download(self, url: str):
        download_service.start(url, if_only_extract=False, if_manual_download=True)

    def retry_download(self, task_id: int):
        with get_session() as session:
            task = session.exec(select(DownloadTask).where(DownloadTask.task_id == task_id)).first()
            if task:
                task.status = 'PENDING'
                task.retry = task.retry + 1
                session.commit()
                download_service.start(task.url, if_only_extract=False, if_retry=True, if_manual_retry=True)
                return True
            return False

    def pause_download(self, task_id: int):
        with get_session() as session:
            task = session.exec(select(DownloadTask).where(DownloadTask.task_id == task_id)).first()
            if task:
                task.status = 'PAUSED'
                session.commit()
                download_service.stop(task.task_id)
                return True
            return False

    def delete_download(self, task_id: int):
        with get_session() as session:
            task = session.exec(select(DownloadTask).where(DownloadTask.task_id == task_id)).first()
            if task:
                session.delete(task)
                session.commit()
                download_service.stop(task.task_id)
                return True
            return False

    def list_tasks(self, status: str, page: int, page_size: int) -> Tuple[List[dict], int]:
        with get_session() as session:
            base_query = select(DownloadTask).where(DownloadTask.title != '')
            count_query = select(func.count(DownloadTask.task_id)).where(DownloadTask.title != '')
            if status:
                base_query = base_query.where(DownloadTask.status == status)
                count_query = count_query.where(DownloadTask.status == status)
            total_tasks = session.exec(count_query).one()
            offset = (page - 1) * page_size

            base_query = base_query.order_by(col(DownloadTask.created_at).desc()).offset(offset).limit(page_size)
            tasks = session.exec(base_query).all()

            client = RedisClient.get_instance().client
            task_convert_list = []
            for task in tasks:
                task_id = task.task_id
                downloaded_size = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'downloaded_size')
                total_size = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'total_size')
                speed = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'speed')
                eta = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'eta')
                percent = client.hget(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}', 'percent')

                task_convert_list.append({
                    "id": task.task_id,
                    "thumbnail": task.thumbnail,
                    "status": task.status,
                    "title": task.title,
                    "channel_name": task.channel_name,
                    "channel_avatar": task.channel_avatar,
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

    def get_task_progress(self, task_ids: List[str]) -> List[dict]:
        client = RedisClient.get_instance().client
        tasks_progress = []
        with get_session() as session:
            for task_id in task_ids:
                progress = client.hgetall(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task_id}')
                task = session.exec(select(DownloadTask).where(DownloadTask.task_id == task_id)).first()
                task_status = task.status if task else None

                if progress:
                    current_type = progress.get('current_type', 'unknown')
                    data = {
                        "task_id": int(task_id),
                        "status": task_status,
                        "current_type": current_type,
                        "downloaded_size": int(progress.get('downloaded_size', 0)),
                        "total_size": int(progress.get('total_size', 0)),
                        "speed": progress.get('speed', '未知'),
                        "eta": progress.get('eta', '未知'),
                        "percent": progress.get('percent', '未知'),
                    }
                    tasks_progress.append(data)
        return tasks_progress

    def get_new_tasks(self, latest_task_id: int) -> List[dict]:
        with get_session() as session:
            new_tasks = session.exec(select(DownloadTask).where(DownloadTask.task_id > latest_task_id).order_by(
                col(DownloadTask.task_id).desc()).limit(10)).all()

            client = RedisClient.get_instance().client
            new_task_data = []
            for task in new_tasks:
                progress = client.hgetall(f'{constants.REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS}:{task.task_id}')
                downloaded_size = int(progress.get('downloaded_size', 0))
                total_size = int(progress.get('total_size', 0))
                speed = progress.get('speed', '未知')
                eta = progress.get('eta', '未知')
                percent = progress.get('percent', '未知')

                new_task_data.append({
                    "id": task.task_id,
                    "thumbnail": task.thumbnail,
                    "status": task.status,
                    "title": task.title,
                    "channel_name": task.channel_name,
                    "channel_avatar": task.channel_avatar,
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

            return new_task_data
