from sqlalchemy import select

from core.database import get_session
from models.task.download_task import DownloadTask
from models.task.task_state import TaskState


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
