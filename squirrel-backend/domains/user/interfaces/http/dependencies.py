from domains.user.application.services.config import UserConfigService
from domains.user.application.services.service import UserService


def get_config_service() -> UserConfigService:
    return UserConfigService()


def get_user_service() -> UserService:
    return UserService()
