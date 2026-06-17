import logging

from fastapi import APIRouter, Depends

from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from domains.video.application.services.crud import save_remote_video as save_remote_video_record
from domains.video.application.services.listing.service import get_video as get_video_detail
from domains.video.interfaces.dto.request.video import RemoteVideoSaveRequest
from infrastructure.http import response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/remote-save')
def save_remote_video(
    data: RemoteVideoSaveRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        video = save_remote_video_record(data.model_dump())
        return response.success(get_video_detail(current_user.id, video.id))
    except ValueError as exc:
        return response.param_error(str(exc))
    except Exception:
        logger.exception('Failed to save remote video')
        return response.server_error('保存远端视频失败')
