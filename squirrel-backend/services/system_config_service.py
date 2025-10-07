from typing import Any, Dict, List, Optional
import logging
import os

from core.database import get_session
from models.system_config import SystemConfig

# bool 转换集合
TRUE_SET = {"true", "1", "yes", "y", "on"}
FALSE_SET = {"false", "0", "no", "n", "off"}


def _to_bool(val: Optional[str], default: bool) -> bool:
    if val is None:
        return default
    v = str(val).strip().lower()
    if v in TRUE_SET:
        return True
    if v in FALSE_SET:
        return False
    return default


def _from_bool(val: bool) -> str:
    return "true" if bool(val) else "false"


def get_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    读取指定 key 的值，若不存在返回 default
    """
    with get_session() as session:
        row = session.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row is None:
            return default
        return row.value


def set_value(key: str, value: str) -> None:
    """
    设置/更新指定 key 的值
    """
    with get_session() as session:
        row = session.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row is None:
            row = SystemConfig(key=key, value=value)
            session.add(row)
        else:
            row.value = value
        session.commit()
        logging.getLogger().info(f"[system_config] set %s=%s", key, value)


def get_bool(key: str, default: bool) -> bool:
    """
    读取布尔配置，使用 'true'/'false' 等字符串解析
    
    优先级：环境变量 > 数据库配置 > 默认值
    环境变量命名规则：将 key 转为大写
    例如: enable_scheduler -> ENABLE_SCHEDULER
    """
    # 1. 优先检查环境变量
    env_key = key.upper()
    env_value = os.getenv(env_key)
    if env_value is not None:
        result = _to_bool(env_value, default)
        logging.getLogger().debug(f"[system_config] get_bool({key}) from env {env_key}={env_value} -> {result}")
        return result
    
    # 2. 从数据库读取
    db_value = get_value(key, None)
    result = _to_bool(db_value, default)
    if db_value is not None:
        logging.getLogger().debug(f"[system_config] get_bool({key}) from database={db_value} -> {result}")
    else:
        logging.getLogger().debug(f"[system_config] get_bool({key}) using default -> {result}")
    return result


def set_bool(key: str, value: bool) -> None:
    """
    写入布尔配置，统一存储为 'true'/'false'
    """
    set_value(key, _from_bool(value))


def get_many(keys: List[str], defaults: Dict[str, Any]) -> Dict[str, str]:
    """
    批量读取，返回 key->value 字典；不存在的 key 使用 defaults 中的默认字符串或空串
    """
    with get_session() as session:
        if not keys:
            return {}
        rows = session.query(SystemConfig).filter(SystemConfig.key.in_(keys)).all()
        result: Dict[str, str] = {}
        found_keys = set()
        for r in rows:
            result[r.key] = r.value
            found_keys.add(r.key)
        for k in keys:
            if k not in found_keys:
                dv = defaults.get(k)
                result[k] = "" if dv is None else str(dv)
        return result