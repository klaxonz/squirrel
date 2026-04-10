from datetime import datetime, timedelta
from typing import Optional, Dict

from fastapi import APIRouter, Depends, Request, Response
from common import response
from models.user import User
from pydantic import BaseModel, EmailStr, Field, SecretStr, model_validator
from services import user_service, user_config_service
from utils.jwt_helper import TOKEN_VERSION_CLAIM, clear_auth_cookie, create_access_token, get_current_user, set_auth_cookie

router = APIRouter(prefix="/api/users", tags=["users"])


class UserRegisterRequest(BaseModel):
    nickname: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserPasswordUpdateRequest(BaseModel):
    current_password: SecretStr
    new_password: SecretStr = Field(..., min_length=8)

    @model_validator(mode='after')
    def validate_passwords(self):
        if self.current_password.get_secret_value() == self.new_password.get_secret_value():
            raise ValueError('新密码不能与当前密码相同')
        return self


class UserConfigUpdate(BaseModel):
    settings: Dict = Field(..., example={"showNsfw": False})
    merge: Optional[bool] = False

    @model_validator(mode='after')
    def validate_settings(self):
        allowed_keys = {'showNsfw', 'autoplay', 'autoplayNext', 'loop'}
        for key in self.settings:
            if key not in allowed_keys:
                raise ValueError(f"无效的配置项: {key}")
        if 'showNsfw' in self.settings and not isinstance(self.settings['showNsfw'], bool):
            raise ValueError("showNsfw必须是布尔值")
        if 'autoplay' in self.settings and not isinstance(self.settings['autoplay'], bool):
            raise ValueError("autoplay必须是布尔值")
        if 'autoplayNext' in self.settings and not isinstance(self.settings['autoplayNext'], bool):
            raise ValueError("autoplayNext必须是布尔值")
        if 'loop' in self.settings and not isinstance(self.settings['loop'], bool):
            raise ValueError("loop必须是布尔值")
        return self


# Response Models
class UserResponse(BaseModel):
    id: int
    nickname: str
    email: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


def _serialize_user(user: User) -> dict:
    return user.to_dict(exclude={'token_version'})


def _issue_auth_cookie(http_response: Response, http_request: Request, user: User) -> None:
    access_token = create_access_token(
        data={
            'sub': str(user.id),
            TOKEN_VERSION_CLAIM: int(getattr(user, 'token_version', 0) or 0),
        },
        expires_delta=timedelta(days=30)
    )
    set_auth_cookie(http_response, access_token, http_request)


@router.post("/register")
async def register(request: UserRegisterRequest):
    """
    Register a new user
    """
    try:
        user, _ = user_service.create_user(
            nickname=request.nickname,
            email=str(request.email),
            password=request.password
        )
        return response.success(
            data=_serialize_user(user),
            msg="注册成功"
        )
    except ValueError as e:
        return response.param_error(str(e))


@router.post("/login")
async def login(request: UserLoginRequest, http_request: Request, http_response: Response):
    """
    User login
    """
    result = user_service.authenticate(str(request.email), request.password)
    if not result:
        return response.error("邮箱或密码错误")

    user, _account = result
    _ = _account
    _issue_auth_cookie(http_response, http_request, user)

    return response.success(
        data=_serialize_user(user),
        msg="登录成功"
    )


@router.post('/logout')
async def logout(http_request: Request, http_response: Response):
    clear_auth_cookie(http_response, http_request)
    return response.success(msg='退出成功')


@router.get("/me")
async def get_current_user_info(current_user=Depends(get_current_user)):
    """
    Get current user info
    """
    return response.success(
        data=_serialize_user(current_user)
    )


@router.put("/me")
async def update_user(
        request: UserUpdateRequest,
        current_user=Depends(get_current_user)
):
    """
    Update current user info
    """
    try:
        updated_user = user_service.update_user(current_user.id, **request.model_dump())
        return response.success(
            data=_serialize_user(updated_user),
            msg="更新成功"
        )
    except ValueError as e:
        return response.param_error(str(e))


@router.put('/me/password')
async def update_password(
    request: UserPasswordUpdateRequest,
    http_request: Request,
    http_response: Response,
    current_user: User = Depends(get_current_user)
):
    try:
        updated_user, _ = user_service.update_password(
            current_user.id,
            request.current_password.get_secret_value(),
            request.new_password.get_secret_value(),
        )
        _issue_auth_cookie(http_response, http_request, updated_user)
        return response.success(
            data=_serialize_user(updated_user),
            msg='密码修改成功，旧会话已失效'
        )
    except ValueError as e:
        return response.param_error(str(e))


@router.post('/me/revoke-sessions')
async def revoke_sessions(
    http_request: Request,
    http_response: Response,
    current_user: User = Depends(get_current_user)
):
    try:
        updated_user = user_service.rotate_token_version(current_user.id)
        _issue_auth_cookie(http_response, http_request, updated_user)
        return response.success(
            data=_serialize_user(updated_user),
            msg='已撤销其他会话'
        )
    except ValueError as e:
        return response.param_error(str(e))


@router.get("/{user_id}")
async def get_user(user_id: int):
    """
    Get user by ID
    """
    user = user_service.get_user_by_id(user_id)
    if not user:
        return response.not_found(f"用户 {user_id} 不存在")
    return response.success(
        data=_serialize_user(user)
    )


@router.get("/me/config")
async def get_user_config(
    current_user: User = Depends(get_current_user),
):
    settings = user_config_service.get_config(current_user.id)
    return response.success(data=settings)


@router.put("/me/config")
async def update_user_config(
    config_data: UserConfigUpdate,
    current_user: User = Depends(get_current_user),
):
    updated = user_config_service.update_config(
        user_id=current_user.id,
        new_settings=config_data.settings,
        merge=config_data.merge
    )
    return response.success(data=updated, msg="配置更新成功")
