from fastapi import APIRouter, Depends, Request, Response

from domains.user.application.services.service import UserService
from infrastructure.auth.jwt import clear_auth_cookie
from infrastructure.http import response

from .auth_cookie import issue_auth_cookie, serialize_user
from .dependencies import get_user_service
from .schemas import UserLoginRequest, UserRegisterRequest

router = APIRouter()


@router.post('/register')
async def register(
    request: UserRegisterRequest,
    user_svc: UserService = Depends(get_user_service),
):
    """Register a new user.

    Conflict (email already registered) surfaces as a 409 via the global
    ``DomainError`` handler -- no per-route try/except needed.
    """
    user, _ = user_svc.create_user(
        nickname=request.nickname,
        email=str(request.email),
        password=request.password,
    )
    return response.success(
        data=serialize_user(user),
        msg='注册成功',
    )


@router.post('/login')
async def login(
    request: UserLoginRequest,
    http_request: Request,
    http_response: Response,
    user_svc: UserService = Depends(get_user_service),
):
    """User login"""
    result = user_svc.authenticate(str(request.email), request.password)
    if not result:
        return response.error('邮箱或密码错误')

    user, _account = result
    _ = _account
    issue_auth_cookie(http_response, http_request, user, remember_me=request.remember_me)

    return response.success(
        data=serialize_user(user),
        msg='登录成功',
    )


@router.post('/logout')
async def logout(http_request: Request, http_response: Response):
    clear_auth_cookie(http_response, http_request)
    return response.success(msg='退出成功')
