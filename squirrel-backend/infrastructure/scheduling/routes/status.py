from fastapi import APIRouter, Depends

from infrastructure.http import response
from infrastructure.scheduling.lifecycle import scheduler_status
from infrastructure.scheduling.routes.dependencies import get_scheduled_task_service
from infrastructure.scheduling.service import ScheduledTaskService

router = APIRouter()


@router.get('/status')
def get_scheduler_status():
    """Get scheduler running status."""
    return response.success(scheduler_status())


@router.get('/statistics')
def get_task_statistics(svc: ScheduledTaskService = Depends(get_scheduled_task_service)):
    """Get task statistics."""
    return response.success(svc.get_task_statistics())
