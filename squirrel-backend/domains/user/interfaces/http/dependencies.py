from fastapi import Request

from domains.user.application.services.config import UserConfigService
from domains.user.application.services.service import UserService


def get_config_service(request: Request) -> UserConfigService:
    return request.app.state.user_config_service


def get_user_service(request: Request) -> UserService:
    return request.app.state.user_service
