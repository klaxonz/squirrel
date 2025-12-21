import logging
from typing import Optional
from fastapi import APIRouter
from common.constants import SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER, SYS_BLUR_NSFW_THUMBNAILS
from fastapi import Body
from services import system_config_service

router = APIRouter(prefix="/api/system/config", tags=["system-config"])
_logger = logging.getLogger()


def to_bool(val: Optional[str]) -> Optional[bool]:
    """
    将字符串值转换为布尔值
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
    """
    将配置字典中的特定键转换为正确的数据类型
    """
    # 定义需要转换为布尔值的配置项
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
    """
    返回数据库中已有的所有系统配置，并将特定配置项转换为正确的数据类型。
    """
    config_dict = system_config_service.get_all_configs()
    return _convert_config_types(config_dict)


@router.post("")
async def update_system_config(payload: dict = Body(...)):
    """
    通用更新接口：仅支持 JSON Body，逐项写入 system_config（纯字符串存储）。
    返回：数据库中当前所有配置（纯 KV 字符串）
    """
    for k, v in payload.items():
        system_config_service.set_value(k, str(v))

    config_dict = system_config_service.get_all_configs()
    return _convert_config_types(config_dict)
