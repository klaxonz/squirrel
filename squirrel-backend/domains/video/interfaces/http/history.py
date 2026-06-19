from fastapi import APIRouter, Body, Depends

from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from domains.video.application.services.history.service import VideoHistoryService
from domains.video.interfaces.dto.video_history import (
    HistoryBatchUpdate,
    HistoryCreate,
)
from domains.video.interfaces.http.query_params import VideoHistoryListQuery
from infrastructure.http import response

router = APIRouter(
    prefix='/api/video-history',
    tags=['视频历史记录'],
)


def get_video_history_service():
    return VideoHistoryService()


@router.post('/update')
def update_history(
    data: HistoryCreate,
    current_user: User = Depends(get_current_user),
    svc: VideoHistoryService = Depends(get_video_history_service),
):
    svc.update_history(current_user.id, data)
    return response.success()


@router.post('/batch-update')
def batch_update_history(
    data: HistoryBatchUpdate,
    current_user: User = Depends(get_current_user),
    svc: VideoHistoryService = Depends(get_video_history_service),
):
    svc.batch_update_histories(current_user.id, data.reports)
    return response.success()


@router.get('/list')
def get_history_list(
    params: VideoHistoryListQuery = Depends(),
    current_user: User = Depends(get_current_user),
    svc: VideoHistoryService = Depends(get_video_history_service),
):
    filters = {
        'video_id': params.video_id,
        'min_duration': params.min_duration,
        'start_date': params.start_date,
        'end_date': params.end_date,
        'query': params.query,
        'nsfw': params.nsfw,
        'site': params.site,
    }
    video_histories = svc.list_histories(
        user_id=current_user.id,
        filters={k: v for k, v in filters.items() if v is not None},
        page=params.page,
        page_size=params.page_size,
    )
    return response.success(video_histories)


@router.post('/clear')
def clear_history(
    video_ids: list[int] = Body(None),
    current_user: User = Depends(get_current_user),
    svc: VideoHistoryService = Depends(get_video_history_service),
):
    svc.clear_histories(
        user_id=current_user.id,
        video_ids=video_ids,
    )
    return response.success()


@router.delete('/{history_id}')
def delete_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    svc: VideoHistoryService = Depends(get_video_history_service),
):
    deleted_count = svc.delete_history(current_user.id, history_id)
    if deleted_count == 0:
        return response.not_found('历史记录不存在')
    return response.success()
