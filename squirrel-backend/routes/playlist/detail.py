from fastapi import APIRouter, Depends

from common import response
from models.user import User
from routes.playlist.dependencies import get_playlist_command_service, get_playlist_query_service
from schemas.playlist import PlaylistUpdate
from services.playlist.commands import PlaylistCommandService
from services.playlist.queries import PlaylistQueryService
from services.user.auth import get_current_user

router = APIRouter()


@router.get('/{playlist_id}')
def get_playlist_detail(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    svc: PlaylistQueryService = Depends(get_playlist_query_service),
):
    detail = svc.get_playlist_detail(current_user.id, playlist_id)
    if not detail:
        return response.not_found('播放列表不存在')
    return response.success(detail)


@router.get('/{playlist_id}/items')
def get_playlist_items(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    svc: PlaylistQueryService = Depends(get_playlist_query_service),
):
    playlist_items = svc.get_playlist_items_with_videos(current_user.id, playlist_id)
    if playlist_items is None:
        return response.not_found('播放列表不存在')
    return response.success(playlist_items)


@router.put('/{playlist_id}')
def update_playlist(
    playlist_id: int,
    data: PlaylistUpdate,
    current_user: User = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    try:
        playlist = svc.update_playlist(current_user.id, playlist_id, data)
        if not playlist:
            return response.not_found('播放列表不存在')
        return response.success(playlist)
    except ValueError as e:
        return response.param_error(str(e))


@router.delete('/{playlist_id}')
def delete_playlist(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    try:
        ok = svc.delete_playlist(current_user.id, playlist_id)
        if not ok:
            return response.not_found('播放列表不存在')
        return response.success({'deleted': True})
    except ValueError as e:
        return response.param_error(str(e))
