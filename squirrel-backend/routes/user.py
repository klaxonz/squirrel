from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from common import response
from services import user_service
from utils.jwt_helper import create_access_token, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


# Request Models
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


# Response Models
class UserResponse(BaseModel):
    id: int
    nickname: str
    email: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


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
            data=user.to_dict(),
            msg="注册成功"
        )
    except ValueError as e:
        return response.param_error(str(e))


@router.post("/login")
async def login(request: UserLoginRequest):
    """
    User login
    """
    result = user_service.authenticate(str(request.email), request.password)
    if not result:
        return response.error("邮箱或密码错误")

    user, account = result
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=30)
    )

    return response.success(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": user.to_dict()
        },
        msg="登录成功"
    )


@router.get("/me")
async def get_current_user_info(current_user=Depends(get_current_user)):
    """
    Get current user info
    """
    return response.success(
        data=current_user.to_dict()
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
            data=updated_user.to_dict(),
            msg="更新成功"
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
        data=user.to_dict()
    )
