from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from services.music.service import MusicService
from services.user.auth import get_current_user

from .dependencies import get_music_service

router = APIRouter()
@router.get("/ranks")
async def list_music_ranks(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_ranks(current_user.id))


@router.get("/rank/tracks")
async def get_music_rank_tracks(
    rank_id: str = Query(..., min_length=1, description="排行榜 ID"),
    rank_cid: str | None = Query(None, description="排行榜期次 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_rank_tracks(current_user.id, rank_id, rank_cid, page, page_size))


@router.get("/rank/detail")
async def get_music_rank_detail(
    rank_id: str = Query(..., min_length=1, description="排行榜 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_rank_detail(current_user.id, rank_id))


@router.get("/playlists")
async def list_music_playlists(
    category_id: int = Query(0, ge=0, description="歌单分类 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_playlists(current_user.id, category_id, page, page_size))


@router.get("/playlist/tags")
async def list_music_playlist_tags(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_playlist_tags(current_user.id))


@router.get("/playlist/similar")
async def get_music_similar_playlists(
    playlist_id: str = Query(..., min_length=1, description="歌单 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_similar_playlists(current_user.id, playlist_id))


@router.get("/playlist/tracks")
async def get_music_playlist_tracks(
    playlist_id: str = Query(..., min_length=1, description="歌单 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_playlist_tracks(current_user.id, playlist_id, page, page_size))


@router.get("/artist/detail")
async def get_music_artist_detail(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_detail(current_user.id, artist_id))


@router.get("/artist/tracks")
async def get_music_artist_tracks(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_tracks(current_user.id, artist_id, page, page_size))


@router.get("/artist/albums")
async def get_music_artist_albums(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_albums(current_user.id, artist_id, page, page_size))


@router.get("/artist/videos")
async def get_music_artist_videos(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_videos(current_user.id, artist_id, page, page_size))


@router.get("/artist/honour")
async def get_music_artist_honour(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_honour(current_user.id, artist_id))


@router.get("/artists/directory")
async def list_music_artist_directory(
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_artist_directory(current_user.id, page, page_size))


@router.get("/album/detail")
async def get_music_album_detail(
    album_id: str = Query(..., min_length=1, description="专辑 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_album_detail(current_user.id, album_id))


@router.get("/album/tracks")
async def get_music_album_tracks(
    album_id: str = Query(..., min_length=1, description="专辑 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_album_tracks(current_user.id, album_id, page, page_size))
