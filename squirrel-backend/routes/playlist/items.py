from fastapi import APIRouter, Depends

from common import response
from models.user import User
from routes.playlist.dependencies import get_playlist_command_service
from schemas.playlist import PlaylistItemAdd, PlaylistItemReorder
from services.playlist.commands import PlaylistCommandService
from services.user.auth import get_current_user

router = APIRouter()


@router.post('/items')
def add_video_to_playlist(
    data: PlaylistItemAdd,
    current_user: User = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
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
        if 'Video not found' in msg:
            return response.not_found(msg)
        if 'Playlist not found' in msg:
            return response.not_found(msg)
        return response.param_error(msg)


@router.delete('/{playlist_id}/items/{video_id}')
def remove_video_from_playlist(
    playlist_id: int,
    video_id: int,
    current_user: User = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    ok = svc.remove_video_from_playlist(current_user.id, playlist_id, video_id)
    if not ok:
        return response.not_found('播放列表项不存在')
    return response.success({'removed': True})


@router.put('/items/reorder')
def reorder_playlist_item(
    data: PlaylistItemReorder,
    current_user: User = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    try:
        item = svc.reorder_playlist_item(current_user.id, data)
        if not item:
            return response.not_found('播放列表项不存在')
        return response.success(item)
    except ValueError as e:
        return response.param_error(str(e))
