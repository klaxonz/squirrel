from fastapi import APIRouter, Depends, Query

from domains.playlist.interfaces.http.dependencies import get_playlist_playback_service
from domains.playlist.application.services.playback import PlaylistPlaybackService
from shared_kernel.application import response
from domains.user.domain.models.user import User
from domains.user.application.services.auth import get_current_user

router = APIRouter()


@router.post('/{playlist_id}/play-next')
def play_next_video(
    playlist_id: int,
    video_id: int = Query(..., description='当前播放的视频ID'),
    current_user: User = Depends(get_current_user),
    svc: PlaylistPlaybackService = Depends(get_playlist_playback_service),
):
    result = svc.play_next_video(current_user.id, playlist_id, video_id)
    if result is None:
        return response.not_found('播放列表不存在')
    if 'error' in result:
        return response.not_found(result['error'])
    return response.success(result)
