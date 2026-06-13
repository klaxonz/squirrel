from fastapi import APIRouter

from common import response
from scheduling.lifecycle import scheduler_status
from scheduling.service import ScheduledTaskService

router = APIRouter()


@router.get('/status')
def get_scheduler_status():
    """Get scheduler running status."""
    return response.success(scheduler_status())


@router.get('/statistics')
def get_task_statistics():
    """Get task statistics."""
    return response.success(ScheduledTaskService.get_task_statistics())
