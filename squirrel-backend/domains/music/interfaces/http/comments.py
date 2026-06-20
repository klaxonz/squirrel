from fastapi import APIRouter, Depends, Query

from domains.music.application.services.service import MusicService
from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response

from .dependencies import get_music_service

router = APIRouter()


@router.get('/comment/song')
async def get_music_song_comments(
    mixsong_id: str = Query(..., alias='mixsongid', min_length=1, description='歌曲 mixsongid'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_song_comments(current_user.id, mixsong_id, page, page_size))


@router.get('/comment/song/classify')
async def get_music_song_comments_classify(
    mixsong_id: str = Query(..., alias='mixsongid', min_length=1, description='歌曲 mixsongid'),
    type_id: str = Query(..., min_length=1, description='分类 type_id'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_song_comments_classify(current_user.id, mixsong_id, type_id, page, page_size),
    )


@router.get('/comment/song/hotword')
async def get_music_song_comments_hotword(
    mixsong_id: str = Query(..., alias='mixsongid', min_length=1, description='歌曲 mixsongid'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_song_comments_hotword(current_user.id, mixsong_id))


@router.get('/comment/floor')
async def get_music_floor_comments(
    special_id: str = Query(..., min_length=1, description='评论 special_id'),
    mixsong_id: str | None = Query(None, alias='mixsongid', description='歌曲 mixsongid'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_floor_comments(current_user.id, special_id, mixsong_id, page, page_size)
    )


@router.get('/comment/playlist')
async def get_music_playlist_comments(
    playlist_id: str = Query(..., min_length=1, description='歌单 ID'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_playlist_comments(current_user.id, playlist_id, page, page_size))


@router.get('/comment/album')
async def get_music_album_comments(
    album_id: str = Query(..., min_length=1, description='专辑 ID'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_album_comments(current_user.id, album_id, page, page_size))


@router.get('/comment/count')
async def get_music_comment_counts(
    hash: str = Query(..., min_length=1, description='歌曲 hash'),
    current_user: CurrentUserDto = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_comment_counts(current_user.id, hash))


# --- Artist Follow ---
