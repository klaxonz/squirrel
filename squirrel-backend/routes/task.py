from fastapi import APIRouter, Query

import common.response as response
from schemas.task import DownloadRequest, DownloadChangeStateRequest
from services import task_service

router = APIRouter(tags=['下载任务接口'])


@router.post("/api/task/download")
def start_download(req: DownloadRequest):
    task_service.start_download(req.url)
    return response.success()


@router.post("/api/task/retry")
def retry_download(req: DownloadChangeStateRequest):
    task_service.retry_download(req.task_id)
    return response.success()


@router.post("/api/task/pause")
def pause_download(req: DownloadChangeStateRequest):
    task_service.pause_download(req.task_id)
    return response.success()


@router.post("/api/task/delete")
def delete_download(req: DownloadChangeStateRequest):
    task_service.delete_task(req.task_id)
    return response.success()


@router.get("/api/task/list")
def get_tasks(
        status: str = Query(None, description="任务状态"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="Items per page")
):
    task_convert_list, total_tasks = task_service.list_tasks(status, page, page_size)
    return response.success({
        "page": page,
        "pageSize": page_size,
        "data": task_convert_list,
        "total": total_tasks,
    })






