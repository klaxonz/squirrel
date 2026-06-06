import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from common import response
from common.constants import SYS_ENABLE_SCHEDULER
from processes.managers.scheduler_manager import scheduler_status
from services import system_config_service
from services.scheduled_task_service import ScheduledTaskService

router = APIRouter(prefix="/api/scheduler", tags=["定时任务管理"])
_logger = logging.getLogger(__name__)


# Pydantic models for API
class TaskCreateRequest(BaseModel):
    name: str = Field(..., description="任务名称", min_length=1, max_length=100)
    task_class: str = Field(..., description="任务类名", min_length=1)
    task_type: str = Field(default="user", description="任务类型")
    description: Optional[str] = Field(None, description="任务描述")
    interval: int = Field(default=60, ge=1, description="执行间隔数值")
    unit: str = Field(default="seconds", description="时间单位", pattern="^(seconds|minutes|hours|days)$")
    start_immediately: bool = Field(default=True, description="是否立即执行")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    task_params: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    is_active: bool = Field(default=True, description="是否激活")


class TaskUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="任务名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="任务描述")
    interval: Optional[int] = Field(None, ge=1, description="执行间隔数值")
    unit: Optional[str] = Field(None, description="时间单位", pattern="^(seconds|minutes|hours|days)$")
    start_immediately: Optional[bool] = Field(None, description="是否立即执行")
    max_retries: Optional[int] = Field(None, ge=0, description="最大重试次数")
    task_params: Optional[Dict[str, Any]] = Field(None, description="任务参数")
    is_active: Optional[bool] = Field(None, description="是否激活")


@router.get("/status")
def get_scheduler_status():
    """获取调度器运行状态"""
    return response.success(scheduler_status())


@router.get("/statistics")
def get_task_statistics():
    """获取任务统计信息"""
    return response.success(ScheduledTaskService.get_task_statistics())


@router.get("/tasks")
def get_scheduled_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="任务状态"),
    task_type: Optional[str] = Query(None, description="任务类型")
):
    """获取定时任务列表"""
    return response.success(ScheduledTaskService.get_task_list(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        task_type=task_type
    ))


@router.post("/tasks")
def create_task(request: TaskCreateRequest):
    """创建新任务"""
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
        is_active=request.is_active
    )

    if not task:
        return response.param_error("创建任务失败")

    return response.success(task.to_dict(), "任务创建成功")


@router.put("/tasks/{task_id}")
def update_task(task_id: int, request: TaskUpdateRequest):
    """更新任务配置"""
    result = ScheduledTaskService.update_task(
        task_id=task_id,
        name=request.name,
        description=request.description,
        interval=request.interval,
        unit=request.unit,
        start_immediately=request.start_immediately,
        max_retries=request.max_retries,
        task_params=request.task_params,
        is_active=request.is_active
    )

    if not result:
        return response.not_found("任务不存在或更新失败")

    return response.success(msg="任务更新成功")


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """删除任务"""
    result = ScheduledTaskService.delete_task(task_id)
    if not result:
        return response.not_found("任务不存在或删除失败")

    return response.success(msg="任务删除成功")


@router.post("/tasks/{task_id}/enable")
def enable_task(task_id: int):
    """启用任务"""
    result = ScheduledTaskService.enable_task(task_id)
    if not result:
        return response.not_found("任务不存在或启用失败")

    return response.success(msg="任务已启用")


@router.post("/tasks/{task_id}/disable")
def disable_task(task_id: int):
    """禁用任务"""
    result = ScheduledTaskService.disable_task(task_id)
    if not result:
        return response.not_found("任务不存在或禁用失败")

    return response.success(msg="任务已禁用")


@router.post("/tasks/{task_id}/execute")
def execute_task_now(task_id: int):
    """立即执行任务"""
    result = ScheduledTaskService.execute_task_now(task_id)
    if not result:
        return response.not_found("任务不存在或执行失败")

    return response.success(msg="任务执行请求已提交")


@router.get("/task-classes")
def get_available_task_classes():
    """获取可用的任务类"""
    return response.success(ScheduledTaskService.get_available_task_classes())


@router.post("/enable")
def enable_scheduler():
    """启用调度器"""
    system_config_service.set_value(SYS_ENABLE_SCHEDULER, "true")
    return response.success(msg="调度器已启用")


@router.post("/disable")
def disable_scheduler():
    """禁用调度器"""
    system_config_service.set_value(SYS_ENABLE_SCHEDULER, "false")
    return response.success(msg="调度器已禁用")
