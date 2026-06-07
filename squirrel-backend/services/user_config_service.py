import threading
import time
from collections.abc import Callable, Generator

from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from models.user import UserConfig

SessionFactory = Callable[[], Generator[Session, None, None]]


class UserConfigService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session
        self._config_cache = {}
        self._CACHE_TTL = 60
        self._cache_lock = threading.Lock()

    def get_config(self, user_id: int, use_cache: bool = True) -> dict:
        """Get user config, with 60-second cache enabled by default"""
        # 检查缓存
        if use_cache:
            with self._cache_lock:
                if user_id in self._config_cache:
                    cached_config, cached_time = self._config_cache[user_id]
                    if time.time() - cached_time < self._CACHE_TTL:
                        return cached_config

        # 查询数据库
        with self._session_factory() as session:
            config = session.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not config:
                config = UserConfig(user_id=user_id, settings={})
                session.add(config)
                session.commit()
                session.refresh(config)

            # 更新缓存
            with self._cache_lock:
                self._config_cache[user_id] = (config.settings, time.time())
            return config.settings

    def update_config(
            self,
            user_id: int,
            new_settings: dict,
            merge: bool = False,
    ) -> dict:
        sanitized_settings = new_settings

        # 添加类型验证
        if "showNsfw" in sanitized_settings and not isinstance(sanitized_settings["showNsfw"], bool):
            raise ValueError("showNsfw must be a boolean")
        if "autoplay" in sanitized_settings and not isinstance(sanitized_settings["autoplay"], bool):
            raise ValueError("autoplay must be a boolean")
        if "autoplayNext" in sanitized_settings and not isinstance(sanitized_settings["autoplayNext"], bool):
            raise ValueError("autoplayNext must be a boolean")
        if "loop" in sanitized_settings and not isinstance(sanitized_settings["loop"], bool):
            raise ValueError("loop must be a boolean")

        with self._session_factory() as session:
            config = session.query(UserConfig).filter(UserConfig.user_id == user_id).first()
            if not config:
                config = UserConfig(user_id=user_id, settings=sanitized_settings)
            elif merge:
                config.settings = {**config.settings, **sanitized_settings}
            else:
                config.settings = sanitized_settings
            session.add(config)
            session.commit()
            session.refresh(config)

            # 更新缓存后失效缓存
            with self._cache_lock:
                self._config_cache.pop(user_id, None)

            return config.settings


# Default singleton for backward compatibility
_default = UserConfigService()
get_config = _default.get_config
update_config = _default.update_config
