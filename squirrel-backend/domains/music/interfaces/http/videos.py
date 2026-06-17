from fastapi import APIRouter, Depends, Query

from domains.music.application.services.service import MusicService
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from infrastructure.http import response

from .dependencies import get_music_service

router = APIRouter()
@router.get("/video/detail")
async def get_music_video_detail(
    video_id: str = Query(..., min_length=1, description="视频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_video_detail(current_user.id, video_id))


@router.get("/video/url")
async def get_music_video_url(
    video_id: str = Query(..., min_length=1, description="视频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_video_url(current_user.id, video_id))


@router.get("/video/privilege")
async def get_music_video_privilege(
    video_id: str = Query(..., min_length=1, description="视频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_video_privilege(current_user.id, video_id))


# --- Discovery & Recommendation Enhancements ---
