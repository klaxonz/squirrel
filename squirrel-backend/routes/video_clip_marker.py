from fastapi import APIRouter, Depends, Query

import common.response as response
from models.user import User
from schemas.video_clip_marker import ClipMarkerCreate, ClipMarkerPreviewUpload, ClipMarkerUpdate
from services import video_clip_marker_service
from utils.jwt_helper import get_current_user

router = APIRouter(tags=['视频片段标记'])


@router.get('/api/video-clip-markers')
def list_video_clip_markers(
        video_id: int = Query(..., description='视频ID'),
        user: User = Depends(get_current_user),
):
    markers = video_clip_marker_service.list_markers(user.id, video_id)
    return response.success(markers)


@router.post('/api/video-clip-markers')
def create_video_clip_marker(
        data: ClipMarkerCreate,
        user: User = Depends(get_current_user),
):
    try:
        marker = video_clip_marker_service.create_marker(user.id, data)
    except ValueError as exc:
        return response.param_error(str(exc))
    return response.success(marker)


@router.put('/api/video-clip-markers/{marker_id}')
def update_video_clip_marker(
        marker_id: int,
        data: ClipMarkerUpdate,
        user: User = Depends(get_current_user),
):
    try:
        marker = video_clip_marker_service.update_marker(user.id, marker_id, data)
    except ValueError as exc:
        return response.param_error(str(exc))

    if not marker:
        return response.not_found('片段标记不存在')
    return response.success(marker)


@router.post('/api/video-clip-markers/{marker_id}/preview')
def upload_video_clip_marker_preview(
        marker_id: int,
        data: ClipMarkerPreviewUpload,
        user: User = Depends(get_current_user),
):
    try:
        marker = video_clip_marker_service.save_preview(user.id, marker_id, data.image_data_url)
    except ValueError as exc:
        return response.param_error(str(exc))

    if not marker:
        return response.not_found('片段标记不存在')
    return response.success(marker)


@router.delete('/api/video-clip-markers/{marker_id}')
def delete_video_clip_marker(
        marker_id: int,
        user: User = Depends(get_current_user),
):
    deleted_count = video_clip_marker_service.delete_marker(user.id, marker_id)
    if deleted_count == 0:
        return response.not_found('片段标记不存在')
    return response.success()
