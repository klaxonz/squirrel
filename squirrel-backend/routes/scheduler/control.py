from fastapi import APIRouter, Depends

from common import response
from common.constants import SYS_ENABLE_SCHEDULER
from routes.scheduler.dependencies import get_system_config_service
from services.system.config import SystemConfigService

router = APIRouter()


@router.post('/enable')
def enable_scheduler(
    svc: SystemConfigService = Depends(get_system_config_service),
):
    svc.set_value(SYS_ENABLE_SCHEDULER, 'true')
    return response.success(msg='scheduler enabled')


@router.post('/disable')
def disable_scheduler(
    svc: SystemConfigService = Depends(get_system_config_service),
):
    svc.set_value(SYS_ENABLE_SCHEDULER, 'false')
    return response.success(msg='scheduler disabled')
