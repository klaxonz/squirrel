import logging
from collections.abc import Callable, Generator
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from models.system_config import SystemConfig

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Generator[Session, None, None]]

TRUE_SET = {'true', '1', 'yes', 'y', 'on'}
FALSE_SET = {'false', '0', 'no', 'n', 'off'}


class SystemConfigService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    @staticmethod
    def _to_bool(val: str | None, default: bool) -> bool:
        if val is None:
            return default
        v = str(val).strip().lower()
        if v in TRUE_SET:
            return True
        if v in FALSE_SET:
            return False
        return default

    @staticmethod
    def _from_bool(val: bool) -> str:
        return 'true' if bool(val) else 'false'

    def get_value(self, key: str, default: str | None = None) -> str | None:
        with self._session_factory() as session:
            row = session.scalars(select(SystemConfig).where(SystemConfig.key == key)).first()
            if row is None:
                return default
            return row.value

    def set_value(self, key: str, value: str) -> None:
        with self._session_factory() as session:
            row = session.scalars(select(SystemConfig).where(SystemConfig.key == key)).first()
            if row is None:
                row = SystemConfig(key=key, value=value)
                session.add(row)
            else:
                row.value = value
            session.commit()
            logger.info('[system_config] set %s=%s', key, value)

    def get_bool(self, key: str, default: bool) -> bool:
        db_value = self.get_value(key, None)
        bool_val = self._to_bool(db_value, default)
        if db_value is not None:
            logger.debug('[system_config] get_bool(%s) from database=%s -> %s', key, db_value, bool_val)
        else:
            logger.debug('[system_config] get_bool(%s) using default -> %s', key, bool_val)
        return bool_val

    def set_bool(self, key: str, value: bool) -> None:
        self.set_value(key, self._from_bool(value))

    def get_many(self, keys: list[str], defaults: dict[str, Any]) -> dict[str, str]:
        with self._session_factory() as session:
            if not keys:
                return {}
            rows = session.scalars(select(SystemConfig).where(SystemConfig.key.in_(keys))).all()
            config: dict[str, str] = {}
            found_keys = set()
            for r in rows:
                config[r.key] = r.value
                found_keys.add(r.key)
            for k in keys:
                if k not in found_keys:
                    dv = defaults.get(k)
                    config[k] = '' if dv is None else str(dv)
            return config

    def get_all_configs(self) -> dict[str, str]:
        with self._session_factory() as session:
            rows = session.scalars(select(SystemConfig)).all()
            return {row.key: row.value for row in rows}
