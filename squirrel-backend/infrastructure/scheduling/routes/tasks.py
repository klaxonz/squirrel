from fastapi import APIRouter, Depends

from infrastructure.http import response
from infrastructure.scheduling.responses import serialize_scheduled_task
from infrastructure.scheduling.routes.dependencies import get_scheduled_task_service
from infrastructure.scheduling.routes.schemas import TaskCreateRequest, TaskListQuery, TaskUpdateRequest
from infrastructure.scheduling.service import ScheduledTaskService

router = APIRouter()


@router.get('/tasks')
def get_scheduled_tasks(
    params: TaskListQuery = Depends(),
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Get scheduled task list."""
    return response.success(
        svc.get_task_list(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            status=params.status,
            task_type=params.task_type,
        )
    )


@router.post('/tasks')
def create_task(
    request: TaskCreateRequest,
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Create a new task."""
    task = svc.create_task(
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
        return response.param_error('创建任务失败')

    return response.success(serialize_scheduled_task(task), '任务创建成功')


@router.put('/tasks/{task_id}')
def update_task(
    task_id: int,
    request: TaskUpdateRequest,
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Update task configuration."""
    task_result = svc.update_task(
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

    if not task_result:
        return response.not_found('任务不存在或更新失败')

    return response.success(msg='任务更新成功')


@router.delete('/tasks/{task_id}')
def delete_task(
    task_id: int,
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Delete a task."""
    task_result = svc.delete_task(task_id)
    if not task_result:
        return response.not_found('任务不存在或删除失败')

    return response.success(msg='任务删除成功')


@router.post('/tasks/{task_id}/enable')
def enable_task(
    task_id: int,
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Enable a task."""
    task_result = svc.enable_task(task_id)
    if not task_result:
        return response.not_found('任务不存在或启用失败')

    return response.success(msg='任务已启用')


@router.post('/tasks/{task_id}/disable')
def disable_task(
    task_id: int,
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Disable a task."""
    task_result = svc.disable_task(task_id)
    if not task_result:
        return response.not_found('任务不存在或禁用失败')

    return response.success(msg='任务已禁用')


@router.post('/tasks/{task_id}/execute')
def execute_task_now(
    task_id: int,
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Execute a task immediately."""
    task_result = svc.execute_task_now(task_id)
    if not task_result:
        return response.not_found('任务不存在或执行失败')

    return response.success(msg='任务执行请求已提交')


@router.get('/task-classes')
def get_available_task_classes(
    svc: ScheduledTaskService = Depends(get_scheduled_task_service),
):
    """Get available task classes."""
    return response.success(svc.get_available_task_classes())
