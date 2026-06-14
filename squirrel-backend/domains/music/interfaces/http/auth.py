from fastapi import APIRouter, Depends, Query

from domains.music.application.services.service import MusicService
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from shared_kernel.application import response

from .dependencies import get_music_service

router = APIRouter()
@router.get("/auth/status")
async def get_music_auth_status(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_auth_status(current_user.id))


@router.post("/auth/qr")
async def create_music_qr_login(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.create_qr_login())


@router.get("/user/profile")
async def get_music_user_profile(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_profile(current_user.id))


@router.post("/user/logout")
async def logout_music_user(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.logout(current_user.id))


@router.get("/auth/qr/check")
async def check_music_qr_login(
    key: str = Query(..., min_length=1, description="二维码 key"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.check_qr_login(current_user.id, key))


@router.post("/auth/logout")
async def logout_music(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    await music_service.clear_auth(current_user.id)
    return response.success({"ok": True})


@router.post("/auth/captcha")
async def send_music_captcha(
    phone: str = Query(..., min_length=11, max_length=11, description="phone number"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.send_captcha(phone))


@router.post("/auth/login")
async def login_music_cellphone(
    phone: str = Query(..., min_length=11, max_length=11, description="phone number"),
    captcha: str = Query(..., min_length=4, max_length=6, description="captcha code"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.login_cellphone(current_user.id, phone, captcha))
