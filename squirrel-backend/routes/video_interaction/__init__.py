from fastapi import APIRouter, Depends

from common import response
from models.user import User
from schemas.video_interaction import VideoInteractionDelete, VideoInteractionUpdate
from services.user.auth import get_current_user
from services.video.engagement.interaction import VideoInteractionService

router = APIRouter(
    prefix="/api/video-interaction",
    tags=["视频交互"],
)


def get_video_interaction_service() -> VideoInteractionService:
    return VideoInteractionService()


@router.post("/toggle-like")
def update_history(
        data: VideoInteractionUpdate,
        user: User = Depends(get_current_user),
        svc: VideoInteractionService = Depends(get_video_interaction_service),
):
    svc.save_or_update_video_interaction(user.id, data.video_id, data.interaction_type)
    return response.success()


@router.post("/delete")
def delete_history(
        data: VideoInteractionDelete,
        user: User = Depends(get_current_user),
        svc: VideoInteractionService = Depends(get_video_interaction_service),
):
    svc.delete_video_interaction(user.id, data.video_id)
    return response.success()
