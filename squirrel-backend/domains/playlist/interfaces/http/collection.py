from fastapi import APIRouter, Depends

from domains.playlist.application.services.commands import PlaylistCommandService
from domains.playlist.application.services.queries import PlaylistQueryService
from domains.playlist.interfaces.dto.playlist import PlaylistCreate
from domains.playlist.interfaces.http.dependencies import get_playlist_command_service, get_playlist_query_service
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from shared_kernel.application import response

router = APIRouter()


@router.get('/')
def list_playlists(
    current_user: User = Depends(get_current_user),
    svc: PlaylistQueryService = Depends(get_playlist_query_service),
):
    playlists = svc.list_playlists(current_user.id)
    return response.success(playlists)


@router.post('/')
def create_playlist(
    data: PlaylistCreate,
    current_user: User = Depends(get_current_user),
    svc: PlaylistCommandService = Depends(get_playlist_command_service),
):
    try:
        playlist = svc.create_playlist(current_user.id, data)
        return response.success(playlist)
    except ValueError as e:
        return response.param_error(str(e))


@router.get('/default')
def get_default_playlist(
    current_user: User = Depends(get_current_user),
    svc: PlaylistQueryService = Depends(get_playlist_query_service),
):
    playlist = svc.get_default_playlist(current_user.id)
    if not playlist:
        return response.not_found('默认播放列表不存在')
    return response.success(playlist)
