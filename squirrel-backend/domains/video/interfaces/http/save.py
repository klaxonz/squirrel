import logging

from fastapi import APIRouter, Depends

from domains.user.application.services.auth import get_current_user
from domains.user.interfaces.dto.user_dto import CurrentUserDto
from domains.video.application.services.crud import VideoCrudService
from domains.video.application.services.listing.service import VideoListService
from domains.video.interfaces.http.dependencies import get_video_crud_service, get_video_list_service
from domains.video.interfaces.dto.request.video import RemoteVideoSaveRequest
from infrastructure.http import response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/remote-save')
def save_remote_video(
    data: RemoteVideoSaveRequest,
    current_user: CurrentUserDto = Depends(get_current_user),
    crud_svc: VideoCrudService = Depends(get_video_crud_service),
    list_svc: VideoListService = Depends(get_video_list_service),
):
    """Validation errors (missing url/title) surface as 400 via the global
    ``DomainError`` handler; unexpected DB failures still return 500 here."""
    try:
        video = crud_svc.save_remote_video(data.model_dump())
        return response.success(list_svc.get_video(current_user.id, video.id))
    except Exception:
        logger.exception('Failed to save remote video')
        return response.server_error('保存远端视频失败')
