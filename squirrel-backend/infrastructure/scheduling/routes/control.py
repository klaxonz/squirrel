from fastapi import APIRouter, Depends

from domains.system.application.services.config_service import SystemConfigService
from domains.system.domain.models.constants import SYS_ENABLE_SCHEDULER
from infrastructure.http import response
from infrastructure.scheduling.routes.dependencies import get_system_config_service

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
