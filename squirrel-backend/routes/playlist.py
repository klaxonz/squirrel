import logging

from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from schemas.playlist import (
    PlaylistCreate,
    PlaylistItemAdd,
    PlaylistItemReorder,
    PlaylistUpdate,
)
from services.auth_service import get_current_user
from services.playlist_service import PlaylistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/playlist", tags=["播放列表接口"])


def get_playlist_service() -> PlaylistService:
    return PlaylistService()


@router.get("")
def list_playlists(
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    playlists = svc.list_playlists(current_user.id)
    return response.success(playlists)


@router.get("/{playlist_id}")
def get_playlist_detail(
        playlist_id: int,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    detail = svc.get_playlist_detail(current_user.id, playlist_id)
    if not detail:
        return response.not_found("播放列表不存在")
    return response.success(detail)


@router.get("/{playlist_id}/items")
def get_playlist_items(
        playlist_id: int,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    items = svc.get_playlist_items_with_videos(current_user.id, playlist_id)
    if items is None:
        return response.not_found("播放列表不存在")
    return response.success(items)


@router.post("")
def create_playlist(
        data: PlaylistCreate,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    try:
        playlist = svc.create_playlist(current_user.id, data)
        return response.success(playlist)
    except ValueError as e:
        return response.param_error(str(e))


@router.put("/{playlist_id}")
def update_playlist(
        playlist_id: int,
        data: PlaylistUpdate,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    try:
        playlist = svc.update_playlist(current_user.id, playlist_id, data)
        if not playlist:
            return response.not_found("播放列表不存在")
        return response.success(playlist)
    except ValueError as e:
        return response.param_error(str(e))


@router.delete("/{playlist_id}")
def delete_playlist(
        playlist_id: int,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    try:
        ok = svc.delete_playlist(current_user.id, playlist_id)
        if not ok:
            return response.not_found("播放列表不存在")
        return response.success({"deleted": True})
    except ValueError as e:
        return response.param_error(str(e))


@router.post("/items")
def add_video_to_playlist(
        data: PlaylistItemAdd,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    try:
        item = svc.add_video_to_playlist(
            current_user.id,
            data.video_id,
            data.playlist_id,
        )
        return response.success(item)
    except ValueError as e:
        msg = str(e)
        if "Video not found" in msg:
            return response.not_found(msg)
        if "Playlist not found" in msg:
            return response.not_found(msg)
        return response.param_error(msg)


@router.delete("/{playlist_id}/items/{video_id}")
def remove_video_from_playlist(
        playlist_id: int,
        video_id: int,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    ok = svc.remove_video_from_playlist(current_user.id, playlist_id, video_id)
    if not ok:
        return response.not_found("播放列表项不存在")
    return response.success({"removed": True})


@router.put("/items/reorder")
def reorder_playlist_item(
        data: PlaylistItemReorder,
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    try:
        item = svc.reorder_playlist_item(current_user.id, data)
        if not item:
            return response.not_found("播放列表项不存在")
        return response.success(item)
    except ValueError as e:
        return response.param_error(str(e))


@router.get("/default")
def get_default_playlist(
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    playlist = svc.get_default_playlist(current_user.id)
    if not playlist:
        return response.not_found("默认播放列表不存在")
    return response.success(playlist)


@router.post("/{playlist_id}/play-next")
def play_next_video(
        playlist_id: int,
        video_id: int = Query(..., description="当前播放的视频ID"),
        current_user: User = Depends(get_current_user),
        svc: PlaylistService = Depends(get_playlist_service),
):
    result = svc.play_next_video(current_user.id, playlist_id, video_id)
    if result is None:
        return response.not_found("播放列表不存在")
    if "error" in result:
        return response.not_found(result["error"])
    return response.success(result)
