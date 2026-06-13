from fastapi import APIRouter, Depends

from infrastructure.scheduling.routes.dependencies import get_system_config_service
from shared_kernel.application import response
from shared_kernel.system.config import SystemConfigService
from shared_kernel.system.constants import SYS_ENABLE_SCHEDULER

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
