from fastapi import APIRouter, Depends, Query

from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from domains.video.application.services.engagement.clip_marker import VideoClipMarkerService
from domains.video.interfaces.dto.video_clip_marker import ClipMarkerCreate, ClipMarkerPreviewUpload, ClipMarkerUpdate
from infrastructure.http import response

router = APIRouter(prefix="/api/video-clip-markers", tags=["视频片段标记"])


def get_clip_marker_service() -> VideoClipMarkerService:
    return VideoClipMarkerService()


@router.get("")
def list_video_clip_markers(
        video_id: int = Query(..., description="视频ID"),
        user: User = Depends(get_current_user),
        svc: VideoClipMarkerService = Depends(get_clip_marker_service),
):
    markers = svc.list_markers(user.id, video_id)
    return response.success(markers)


@router.post("")
def create_video_clip_marker(
        data: ClipMarkerCreate,
        user: User = Depends(get_current_user),
        svc: VideoClipMarkerService = Depends(get_clip_marker_service),
):
    try:
        marker = svc.create_marker(user.id, data)
    except ValueError as exc:
        return response.param_error(str(exc))
    return response.success(marker)


@router.put("/{marker_id}")
def update_video_clip_marker(
        marker_id: int,
        data: ClipMarkerUpdate,
        user: User = Depends(get_current_user),
        svc: VideoClipMarkerService = Depends(get_clip_marker_service),
):
    try:
        marker = svc.update_marker(user.id, marker_id, data)
    except ValueError as exc:
        return response.param_error(str(exc))

    if not marker:
        return response.not_found("片段标记不存在")
    return response.success(marker)


@router.post("/{marker_id}/preview")
def upload_video_clip_marker_preview(
        marker_id: int,
        data: ClipMarkerPreviewUpload,
        user: User = Depends(get_current_user),
        svc: VideoClipMarkerService = Depends(get_clip_marker_service),
):
    try:
        marker = svc.save_preview(user.id, marker_id, data.image_data_url)
    except ValueError as exc:
        return response.param_error(str(exc))

    if not marker:
        return response.not_found("片段标记不存在")
    return response.success(marker)


@router.delete("/{marker_id}")
def delete_video_clip_marker(
        marker_id: int,
        user: User = Depends(get_current_user),
        svc: VideoClipMarkerService = Depends(get_clip_marker_service),
):
    deleted_count = svc.delete_marker(user.id, marker_id)
    if deleted_count == 0:
        return response.not_found("片段标记不存在")
    return response.success()
