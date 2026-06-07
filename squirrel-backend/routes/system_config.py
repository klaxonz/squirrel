import logging

from fastapi import APIRouter, Body

from common.constants import SYS_BLUR_NSFW_THUMBNAILS, SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER
from services import system_config_service

router = APIRouter(prefix="/api/system/config", tags=["system-config"])
_logger = logging.getLogger(__name__)


def to_bool(val: str | None) -> bool | None:
    """Convert string value to boolean
    """
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("true", "1", "yes", "y", "on"):
        return True
    if s in ("false", "0", "no", "n", "off"):
        return False
    return None


def _convert_config_types(config_dict: dict) -> dict:
    """Convert specific keys in config dict to correct data types
    """
    # Boolean config keys
    boolean_configs = {SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER, SYS_BLUR_NSFW_THUMBNAILS}

    result = {}
    for key, value in config_dict.items():
        if key in boolean_configs:
            result[key] = to_bool(value)
        else:
            result[key] = value
    return result


@router.get("")
def get_system_config():
    """Return all system config from database, converting specific keys to proper types.
    """
    config_dict = system_config_service.get_all_configs()
    return _convert_config_types(config_dict)


@router.post("")
async def update_system_config(payload: dict = Body(...)):
    """Generic update endpoint: accepts JSON Body, writes each key to system_config (plain string storage).
    Returns: all current config from database (plain KV strings)
    """
    for k, v in payload.items():
        system_config_service.set_value(k, str(v))

    config_dict = system_config_service.get_all_configs()
    return _convert_config_types(config_dict)
