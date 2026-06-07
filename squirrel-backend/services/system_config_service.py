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
    """Read value for the given key, return default if not found
    """
    with get_session() as session:
        row = session.scalars(select(SystemConfig).where(SystemConfig.key == key)).first()
        if row is None:
            return default
        return row.value


def set_value(key: str, value: str) -> None:
    """Set/update value for the given key
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
    """Read boolean config, parsing strings like 'true'/'false'

    Priority: database config > default value
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
    """Write boolean config, uniformly stored as 'true'/'false'
    """
    set_value(key, _from_bool(value))


def get_many(keys: list[str], defaults: dict[str, Any]) -> dict[str, str]:
    """Batch read, returns key->value dict; missing keys use defaults or empty string
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
    """Get all system configurations
    """
    with get_session() as session:
        rows = session.scalars(select(SystemConfig)).all()
        return {row.key: row.value for row in rows}
