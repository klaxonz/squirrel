from fastapi import APIRouter, Depends

from common import response
from models.user import User
from schemas.video_interaction import VideoInteractionDelete, VideoInteractionUpdate
from services import video_interaction_service
from utils.jwt_helper import get_current_user

router = APIRouter(
    prefix="/api/video-interaction",
    tags=["视频交互"],
)


@router.post("/toggle-like")
def update_history(
        data: VideoInteractionUpdate,
        user: User = Depends(get_current_user),
):
    video_interaction_service.save_or_update_video_interaction(user.id, data.video_id, data.interaction_type)
    return response.success()


@router.post("/delete")
def delete_history(
        data: VideoInteractionDelete,
        user: User = Depends(get_current_user),
):
    video_interaction_service.delete_video_interaction(user.id, data.video_id)
    return response.success()
