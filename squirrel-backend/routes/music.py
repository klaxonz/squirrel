from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from services import music_service
from utils.jwt_helper import get_current_user

router = APIRouter(tags=['音乐接口'])


@router.get('/api/music/search')
def search_music(
    query: str = Query(..., min_length=1, max_length=100, description='搜索关键词'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error('query cannot be empty')

    try:
        return response.success(music_service.search_tracks(current_user.id, normalized_query, page, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/auth/status')
def get_music_auth_status(
    current_user: User = Depends(get_current_user),
):
    return response.success(music_service.get_auth_status(current_user.id))


@router.post('/api/music/auth/qr')
def create_music_qr_login(
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.create_qr_login())
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/auth/qr/check')
def check_music_qr_login(
    key: str = Query(..., min_length=1, description='二维码 key'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.check_qr_login(current_user.id, key))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/play-url')
def get_music_play_url(
    hash: str = Query(..., min_length=1, description='音乐 hash'),
    album_audio_id: str | None = Query(None, description='专辑音频 ID'),
    quality: str = Query('128', description='音质'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_track_play_url(current_user.id, hash, album_audio_id, quality))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))
