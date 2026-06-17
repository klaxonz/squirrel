from fastapi import APIRouter, Depends, Query

from domains.music.application.services.service import MusicService
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from infrastructure.http import response

from .dependencies import get_music_service

router = APIRouter()
@router.post("/artist/follow")
async def follow_music_artist(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.follow_artist(current_user.id, artist_id))


@router.delete("/artist/follow")
async def unfollow_music_artist(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.unfollow_artist(current_user.id, artist_id))


@router.get("/artist/follow/newsongs")
async def get_music_followed_artist_new_songs(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_followed_artists_new_songs(current_user.id))


@router.get("/user/followed-artists")
async def get_music_user_followed_artists(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_followed_artists(current_user.id))


# --- Video / MV ---
