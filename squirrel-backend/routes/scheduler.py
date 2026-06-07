import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from common import response
from common.constants import SYS_ENABLE_SCHEDULER
from processes.managers.scheduler_manager import scheduler_status
from services import system_config_service
from services.scheduled_task_service import ScheduledTaskService

router = APIRouter(prefix="/api/scheduler", tags=["Scheduled Task Management"])
_logger = logging.getLogger(__name__)


# Pydantic models for API
class TaskCreateRequest(BaseModel):
    name: str = Field(..., description="Task name", min_length=1, max_length=100)
    task_class: str = Field(..., description="Task class name", min_length=1)
    task_type: str = Field(default="user", description="Task type")
    description: str | None = Field(None, description="Task description")
    interval: int = Field(default=60, ge=1, description="Execution interval value")
    unit: str = Field(default="seconds", description="Time unit", pattern="^(seconds|minutes|hours|days)$")
    start_immediately: bool = Field(default=True, description="Whether to execute immediately")
    max_retries: int = Field(default=3, ge=0, description="Max retry count")
    task_params: dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    is_active: bool = Field(default=True, description="Whether active")


class TaskUpdateRequest(BaseModel):
    name: str | None = Field(None, description="Task name", min_length=1, max_length=100)
    description: str | None = Field(None, description="Task description")
    interval: int | None = Field(None, ge=1, description="Execution interval value")
    unit: str | None = Field(None, description="Time unit", pattern="^(seconds|minutes|hours|days)$")
    start_immediately: bool | None = Field(None, description="Whether to execute immediately")
    max_retries: int | None = Field(None, ge=0, description="Max retry count")
    task_params: dict[str, Any] | None = Field(None, description="Task parameters")
    is_active: bool | None = Field(None, description="Whether active")


@router.get("/status")
def get_scheduler_status():
    """Get scheduler running status"""
    return response.success(scheduler_status())


@router.get("/statistics")
def get_task_statistics():
    """Get task statistics"""
    return response.success(ScheduledTaskService.get_task_statistics())


@router.get("/tasks")
def get_scheduled_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    search: str | None = Query(None, description="Search keyword"),
    status: str | None = Query(None, description="Task status"),
    task_type: str | None = Query(None, description="Task type"),
):
    """Get scheduled task list"""
    return response.success(ScheduledTaskService.get_task_list(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        task_type=task_type,
    ))


@router.post("/tasks")
def create_task(request: TaskCreateRequest):
    """Create a new task"""
    task = ScheduledTaskService.create_task(
        name=request.name,
        task_class=request.task_class,
        task_type=request.task_type,
        description=request.description,
        interval=request.interval,
        unit=request.unit,
        start_immediately=request.start_immediately,
        max_retries=request.max_retries,
        task_params=request.task_params,
        is_active=request.is_active,
    )

    if not task:
        return response.param_error("创建任务失败")

    return response.success(task.to_dict(), "任务创建成功")


@router.put("/tasks/{task_id}")
def update_task(task_id: int, request: TaskUpdateRequest):
    """Update task configuration"""
    result = ScheduledTaskService.update_task(
        task_id=task_id,
        name=request.name,
        description=request.description,
        interval=request.interval,
        unit=request.unit,
        start_immediately=request.start_immediately,
        max_retries=request.max_retries,
        task_params=request.task_params,
        is_active=request.is_active,
    )

    if not result:
        return response.not_found("任务不存在或更新失败")

    return response.success(msg="任务更新成功")


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """Delete a task"""
    result = ScheduledTaskService.delete_task(task_id)
    if not result:
        return response.not_found("任务不存在或删除失败")

    return response.success(msg="任务删除成功")


@router.post("/tasks/{task_id}/enable")
def enable_task(task_id: int):
    """Enable a task"""
    result = ScheduledTaskService.enable_task(task_id)
    if not result:
        return response.not_found("任务不存在或启用失败")

    return response.success(msg="任务已启用")


@router.post("/tasks/{task_id}/disable")
def disable_task(task_id: int):
    """Disable a task"""
    result = ScheduledTaskService.disable_task(task_id)
    if not result:
        return response.not_found("任务不存在或禁用失败")

    return response.success(msg="任务已禁用")


@router.post("/tasks/{task_id}/execute")
def execute_task_now(task_id: int):
    """Execute a task immediately"""
    result = ScheduledTaskService.execute_task_now(task_id)
    if not result:
        return response.not_found("任务不存在或执行失败")

    return response.success(msg="任务执行请求已提交")


@router.get("/task-classes")
def get_available_task_classes():
    """Get available task classes"""
    return response.success(ScheduledTaskService.get_available_task_classes())


@router.post("/enable")
def enable_scheduler():
    """Enable the scheduler"""
    system_config_service.set_value(SYS_ENABLE_SCHEDULER, "true")
    return response.success(msg="调度器已启用")


@router.post("/disable")
def disable_scheduler():
    """Disable the scheduler"""
    system_config_service.set_value(SYS_ENABLE_SCHEDULER, "false")
    return response.success(msg="调度器已禁用")
