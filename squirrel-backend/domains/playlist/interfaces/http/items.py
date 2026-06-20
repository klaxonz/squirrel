from fastapi import APIRouter, Depends

from domains.playlist.application.services.commands import PlaylistCommandService
from domains.playlist.interfaces.dto.playlist import PlaylistItemAdd, PlaylistItemReorder
from domains.playlist.interfaces.http.dependencies import get_playlist_command_service
from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from infrastructure.http import response

router = APIRouter()


@router.post('/items')
def add_video_to_playlist(
    data: PlaylistItemAdd,
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    """Missing video/playlist surface as 404 via the global ``DomainError``
    handler."""
    item = svc.add_video_to_playlist(
        current_user.id,
        data.video_id,
        data.playlist_id,
    )
    return response.success(item)


@router.delete('/{playlist_id}/items/{video_id}')
def remove_video_from_playlist(
    playlist_id: int,
    video_id: int,
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    ok = svc.remove_video_from_playlist(current_user.id, playlist_id, video_id)
    if not ok:
        return response.not_found('播放列表项不存在')
    return response.success({'removed': True})


@router.put('/items/reorder')
def reorder_playlist_item(
    data: PlaylistItemReorder,
    current_user: CurrentUserDto = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    item = svc.reorder_playlist_item(current_user.id, data)
    if not item:
        return response.not_found('播放列表项不存在')
    return response.success(item)
