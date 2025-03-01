from fastapi import APIRouter, Depends

from common import response
from models.user import User
from schemas.video_interaction import VideoInteractionUpdate, VideoInteractionDelete
from services import video_interaction_service
from utils.jwt_helper import get_current_user

router = APIRouter(
    tags=['视频交互']
)


@router.post("/api/video-interaction/toggle-like")
def update_history(
        data: VideoInteractionUpdate,
        user: User = Depends(get_current_user)
):
    video_interaction_service.save_or_update_video_interaction(user.id, data.video_id, data.interaction_type)
    return response.success()


@router.post("/api/video-interaction/delete")
def update_history(
        data: VideoInteractionDelete,
        user: User = Depends(get_current_user)
):
    video_interaction_service.delete_video_interaction(user.id, data.video_id)
    return response.success()
