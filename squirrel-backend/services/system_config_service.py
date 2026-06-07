import logging
from typing import Any

from sqlalchemy import select

from core.database import get_session
from models.system_config import SystemConfig

logger = logging.getLogger(__name__)

# bool 转换集合
TRUE_SET = {"true", "1", "yes", "y", "on"}
FALSE_SET = {"false", "0", "no", "n", "off"}


def _to_bool(val: str | None, default: bool) -> bool:
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


def get_value(key: str, default: str | None = None) -> str | None:
    """读取指定 key 的值，若不存在返回 default
    """
    with get_session() as session:
        row = session.scalars(select(SystemConfig).where(SystemConfig.key == key)).first()
        if row is None:
            return default
        return row.value


def set_value(key: str, value: str) -> None:
    """设置/更新指定 key 的值
    """
    with get_session() as session:
        row = session.scalars(select(SystemConfig).where(SystemConfig.key == key)).first()
        if row is None:
            row = SystemConfig(key=key, value=value)
            session.add(row)
        else:
            row.value = value
        session.commit()
        logger.info("[system_config] set %s=%s", key, value)


def get_bool(key: str, default: bool) -> bool:
    """读取布尔配置，使用 'true'/'false' 等字符串解析

    优先级：数据库配置 > 默认值
    """
    # 从数据库读取
    db_value = get_value(key, None)
    result = _to_bool(db_value, default)
    if db_value is not None:
        logger.debug("[system_config] get_bool(%s) from database=%s -> %s", key, db_value, result)
    else:
        logger.debug("[system_config] get_bool(%s) using default -> %s", key, result)
    return result


def set_bool(key: str, value: bool) -> None:
    """写入布尔配置，统一存储为 'true'/'false'
    """
    set_value(key, _from_bool(value))


def get_many(keys: list[str], defaults: dict[str, Any]) -> dict[str, str]:
    """批量读取，返回 key->value 字典；不存在的 key 使用 defaults 中的默认字符串或空串
    """
    with get_session() as session:
        if not keys:
            return {}
        rows = session.scalars(select(SystemConfig).where(SystemConfig.key.in_(keys))).all()
        result: dict[str, str] = {}
        found_keys = set()
        for r in rows:
            result[r.key] = r.value
            found_keys.add(r.key)
        for k in keys:
            if k not in found_keys:
                dv = defaults.get(k)
                result[k] = "" if dv is None else str(dv)
        return result


def get_all_configs() -> dict[str, str]:
    """获取所有系统配置
    """
    with get_session() as session:
        rows = session.scalars(select(SystemConfig)).all()
        return {row.key: row.value for row in rows}
