from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import common.response as response
from common.database import get_db
from schemas.task import DownloadRequest, DownloadChangeStateRequest
from services.task_service import TaskService

router = APIRouter(tags=['下载任务接口'])


@router.post("/api/task/download")
def start_download(req: DownloadRequest, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    task_service.start_download(req.url)
    return response.success()


@router.post("/api/task/retry")
def retry_download(req: DownloadChangeStateRequest, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    success = task_service.retry_download(req.task_id)
    return response.success() if success else response.error("Task not found")


@router.post("/api/task/pause")
def pause_download(req: DownloadChangeStateRequest, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    success = task_service.pause_download(req.task_id)
    return response.success() if success else response.error("Task not found")


@router.post("/api/task/delete")
def delete_download(req: DownloadChangeStateRequest, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    success = task_service.delete_download(req.task_id)
    return response.success() if success else response.error("Task not found")


@router.get("/api/task/list")
def get_tasks(
        status: str = Query(None, description="任务状态"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page"),
        db: Session = Depends(get_db)
):
    task_service = TaskService(db)
    task_convert_list, total_tasks = task_service.list_tasks(status, page, page_size)
    return response.success({
        "page": page,
        "pageSize": page_size,
        "data": task_convert_list,
        "total": total_tasks,
    })


@router.get("/api/task/progress")
async def tasks_progress(task_ids: str, db: Session = Depends(get_db)):
    task_service = TaskService(db)
    task_ids_list = task_ids.split(',')
    tasks_progress = task_service.get_task_progress(task_ids_list)
    return response.success(tasks_progress)


@router.get("/api/task/new_task_notification")
async def new_task_notification(latest_task_id: int = Query(default=0), db: Session = Depends(get_db)):
    task_service = TaskService(db)
    new_task_data = task_service.get_new_tasks(latest_task_id)
    return response.success(new_task_data)
