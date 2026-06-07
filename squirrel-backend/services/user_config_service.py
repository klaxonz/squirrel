import time

from core.database import get_session
from models.user import UserConfig

# 简单的内存缓存（60秒过期）
_config_cache = {}
_CACHE_TTL = 60  # 60秒


def get_config(user_id: int, use_cache: bool = True) -> dict:
    """获取用户配置，默认启用 60 秒缓存"""
    # 检查缓存
    if use_cache and user_id in _config_cache:
        cached_config, cached_time = _config_cache[user_id]
        if time.time() - cached_time < _CACHE_TTL:
            return cached_config

    # 查询数据库
    with get_session() as session:
        config = session.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not config:
            config = UserConfig(user_id=user_id, settings={})
            session.add(config)
            session.commit()
            session.refresh(config)

        # 更新缓存
        _config_cache[user_id] = (config.settings, time.time())
        return config.settings


def update_config(
        user_id: int,
        new_settings: dict,
        merge: bool = False,
) -> dict:
    sanitized_settings = new_settings

    # 添加类型验证
    if "showNsfw" in sanitized_settings and not isinstance(sanitized_settings["showNsfw"], bool):
        raise ValueError("showNsfw必须是布尔值")
    if "autoplay" in sanitized_settings and not isinstance(sanitized_settings["autoplay"], bool):
        raise ValueError("autoplay必须是布尔值")
    if "autoplayNext" in sanitized_settings and not isinstance(sanitized_settings["autoplayNext"], bool):
        raise ValueError("autoplayNext必须是布尔值")
    if "loop" in sanitized_settings and not isinstance(sanitized_settings["loop"], bool):
        raise ValueError("loop必须是布尔值")

    with get_session() as session:
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
        _config_cache.pop(user_id, None)

        return config.settings

