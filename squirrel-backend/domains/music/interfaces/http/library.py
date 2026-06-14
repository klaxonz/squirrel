from fastapi import APIRouter, Depends, Query

from domains.music.application.services.service import MusicService
from domains.music.interfaces.dto.music import (
    MusicPlayHistoryReport,
    MusicPlaylistCollect,
    MusicPlaylistCreate,
    MusicPlaylistTrackAdd,
)
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from shared_kernel.application import response

from .dependencies import get_music_service

router = APIRouter()
@router.get("/user/playlists")
async def list_music_user_playlists(
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_user_playlists(current_user.id, page, page_size))


@router.get("/user/playlist/tracks")
async def get_music_user_playlist_tracks(
    list_id: str = Query(..., min_length=1, description="用户歌单 listid"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_playlist_tracks(current_user.id, list_id, page, page_size))


@router.post("/user/playlists")
async def create_music_user_playlist(
    data: MusicPlaylistCreate,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.create_user_playlist(current_user.id, data.name, data.is_private))


@router.post("/user/playlists/collect")
async def collect_music_playlist(
    data: MusicPlaylistCollect,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.collect_playlist(current_user.id, data.playlist_id))


@router.delete("/user/playlists")
async def delete_music_user_playlist(
    list_id: str = Query(..., min_length=1, description="用户歌单 listid"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.delete_user_playlist(current_user.id, list_id))


@router.post("/user/playlist/tracks")
async def add_music_user_playlist_track(
    data: MusicPlaylistTrackAdd,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.add_track_to_user_playlist(current_user.id, data.list_id, data.track))


@router.delete("/user/playlist/tracks")
async def remove_music_user_playlist_tracks(
    list_id: str = Query(..., min_length=1, description="用户歌单 listid"),
    file_ids: str = Query(..., min_length=1, description="歌曲 fileid，多个用逗号分隔"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.remove_tracks_from_user_playlist(current_user.id, list_id, file_ids))


@router.get("/user/history")
async def get_music_user_history(
    bp: str | None = Query(None, description="上一页返回的 bp"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_history(current_user.id, bp))


@router.get("/user/listen-rank")
async def get_music_user_listen_rank(
    history_type: int = Query(0, alias="type", ge=0, le=1, description="0 最近一周，1 全部累计"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_listen_rank(current_user.id, history_type))


@router.get("/latest-songs/listen")
async def get_music_latest_listen_songs(
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_latest_listen_songs(current_user.id, page_size))


@router.post("/playhistory")
async def upload_music_play_history(
    data: MusicPlayHistoryReport,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.upload_play_history(current_user.id, data.album_audio_id, data.played_at, data.play_count),
    )


@router.get("/favorite/count")
async def get_music_favorite_count(
    mixsongids: str = Query(..., min_length=1, description="音乐 mixsongid，多个用逗号分隔"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_favorite_counts(current_user.id, mixsongids))


@router.get("/user/vip")
async def get_music_user_vip(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_vip_detail(current_user.id))
