from services.user.config import UserConfigService
from services.user.service import UserService


def get_config_service() -> UserConfigService:
    return UserConfigService()


def get_user_service() -> UserService:
    return UserService()
