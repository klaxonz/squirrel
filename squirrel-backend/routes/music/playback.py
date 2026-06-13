from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from services.music.service import MusicService
from services.user.auth import get_current_user

from .dependencies import get_music_service

router = APIRouter()
@router.get("/play-url")
async def get_music_play_url(
    hash: str = Query(..., min_length=1, description="音乐 hash"),
    album_audio_id: str | None = Query(None, description="专辑音频 ID"),
    quality: str = Query("128", description="音质"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_track_play_url(current_user.id, hash, album_audio_id, quality))


@router.get("/song/climax")
async def get_music_track_climax(
    hash: str = Query(..., min_length=1, description="音乐 hash，多个用逗号分隔"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_track_climax(current_user.id, hash))


@router.get("/song/related")
async def get_music_related_tracks(
    album_audio_id: str = Query(..., min_length=1, description="专辑音频 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    sort: str = Query("all", pattern="^(all|hot|new)$", description="排序"),
    type: str | None = Query(None, description="分类"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_related_tracks(current_user.id, album_audio_id, page, page_size, sort, type),
    )


@router.get("/song/mv")
async def get_music_track_mv(
    album_audio_id: str = Query(..., min_length=1, description="专辑音频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_track_mv(current_user.id, album_audio_id))


@router.get("/lyric")
async def get_music_lyric(
    title: str = Query(..., min_length=1, description="歌曲名"),
    artist: str = Query("", description="歌手名"),
    hash: str = Query(..., min_length=1, description="音乐 hash"),
    album_audio_id: str | None = Query(None, description="专辑音频 ID"),
    duration: int = Query(0, ge=0, description="歌曲时长"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_track_lyric(current_user.id, title, artist, hash, album_audio_id, duration),
    )


# --- Comments ---
