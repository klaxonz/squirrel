from typing import Dict

from core.database import get_session
from models.user import UserConfig


def get_config(user_id: int) -> Dict:
    with get_session() as session:
        config = session.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not config:
            default_config = UserConfig(user_id=user_id)
            session.add(default_config)
            session.commit()
        return config.settings


def update_config(
        user_id: int,
        new_settings: Dict,
        merge: bool = False
) -> Dict:
    sanitized_settings = new_settings
    
    # 添加类型验证
    if 'showNsfw' in sanitized_settings and not isinstance(sanitized_settings['showNsfw'], bool):
        raise ValueError("showNsfw必须是布尔值")
    
    with get_session() as session:
        config = session.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not config:
            config = UserConfig(user_id=user_id, settings=sanitized_settings)
        else:
            if merge:
                config.settings = {**config.settings, **sanitized_settings}
            else:
                config.settings = sanitized_settings
        session.add(config)
        session.commit()
        session.refresh(config)
        return config.settings

