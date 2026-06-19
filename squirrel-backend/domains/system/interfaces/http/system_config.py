import logging

from fastapi import APIRouter, Body, Depends

from domains.system.application.services.config_service import SystemConfigService, to_bool
from domains.system.domain.models.constants import SYS_BLUR_NSFW_THUMBNAILS, SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER

router = APIRouter(prefix='/api/system/config', tags=['system-config'])
_logger = logging.getLogger(__name__)


def get_system_config_service():
    return SystemConfigService()


def _convert_config_types(config_dict: dict) -> dict:
    boolean_configs = {SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER, SYS_BLUR_NSFW_THUMBNAILS}
    result = {}
    for key, value in config_dict.items():
        if key in boolean_configs:
            result[key] = to_bool(value)
        else:
            result[key] = value
    return result


@router.get('/')
def get_system_config(
    svc: SystemConfigService = Depends(get_system_config_service),
):
    config_dict = svc.get_all_configs()
    return _convert_config_types(config_dict)


@router.post('/')
async def update_system_config(
    payload: dict = Body(...),
    svc: SystemConfigService = Depends(get_system_config_service),
):
    for k, v in payload.items():
        svc.set_value(k, str(v))

    config_dict = svc.get_all_configs()
    return _convert_config_types(config_dict)
