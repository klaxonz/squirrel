from fastapi import APIRouter, Depends, Request, Response

from domains.user.application.services.auth import get_current_user
from domains.user.application.services.service import UserService
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response

from .auth_cookie import issue_auth_cookie, serialize_user, should_remember_current_session
from .dependencies import get_user_service
from .schemas import UserPasswordUpdateRequest, UserUpdateRequest

router = APIRouter()


@router.get('/me')
async def get_current_user_info(
    current_user: CurrentUserDto = Depends(get_current_user),
    user_svc: UserService = Depends(get_user_service),
):
    """Get current user info.

    The auth dependency only confirms identity (``CurrentUserDto``); profile
    fields are re-read from the store here so the response reflects the
    current DB row rather than whatever the auth path happened to load.
    """
    user = user_svc.get_user_by_id(current_user.id)
    if user is None:
        return response.not_found('用户不存在')
    return response.success(
        data=serialize_user(user),
    )


@router.put('/me')
async def update_user(
    request: UserUpdateRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    user_svc: UserService = Depends(get_user_service),
):
    """Update current user info.

    ``update_user`` returns ``None`` when the user is gone (e.g. deleted
    mid-session); any other validation error surfaces via the global
    ``DomainError`` handler.
    """
    updated_user = user_svc.update_user(current_user.id, **request.model_dump())
    if updated_user is None:
        return response.not_found('用户不存在')
    return response.success(
        data=serialize_user(updated_user),
        msg='更新成功',
    )


@router.put('/me/password')
async def update_password(
    request: UserPasswordUpdateRequest,
    http_request: Request,
    http_response: Response,
    current_user: CurrentUserDto = Depends(get_current_user),
    user_svc: UserService = Depends(get_user_service),
):
    """Errors (wrong password, user missing, etc.) surface via the global
    ``DomainError`` handler with the appropriate status (401/404/400)."""
    updated_user, _ = user_svc.update_password(
        current_user.id,
        request.current_password.get_secret_value(),
        request.new_password.get_secret_value(),
    )
    issue_auth_cookie(
        http_response,
        http_request,
        updated_user,
        remember_me=should_remember_current_session(http_request),
    )
    return response.success(
        data=serialize_user(updated_user),
        msg='密码修改成功,旧会话已失效',
    )


@router.post('/me/revoke-sessions')
async def revoke_sessions(
    http_request: Request,
    http_response: Response,
    current_user: CurrentUserDto = Depends(get_current_user),
    user_svc: UserService = Depends(get_user_service),
):
    updated_user = user_svc.rotate_token_version(current_user.id)
    issue_auth_cookie(
        http_response,
        http_request,
        updated_user,
        remember_me=should_remember_current_session(http_request),
    )
    return response.success(
        data=serialize_user(updated_user),
        msg='已撤销其他会话',
    )


@router.get('/{user_id}')
async def get_user(
    user_id: int,
    user_svc: UserService = Depends(get_user_service),
):
    """Get user by ID"""
    user = user_svc.get_user_by_id(user_id)
    if not user:
        return response.not_found(f'用户 {user_id} 不存在')
    return response.success(
        data=serialize_user(user),
    )
