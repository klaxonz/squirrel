from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query

from common import response
from models.user import User
from schemas.video_history import (
    HistoryBatchUpdate,
    HistoryCreate,
)
from services.auth_service import get_current_user
from services.video_history_service import VideoHistoryService

router = APIRouter(
    prefix='/api/video-history',
    tags=['视频历史记录'],
)


def get_video_history_service():
    return VideoHistoryService()


@router.post('/update')
def update_history(
        data: HistoryCreate,
        user: User = Depends(get_current_user),
        svc: VideoHistoryService = Depends(get_video_history_service),
):
    svc.update_history(user.id, data)
    return response.success()


@router.post('/batch-update')
def batch_update_history(
        data: HistoryBatchUpdate,
        user: User = Depends(get_current_user),
        svc: VideoHistoryService = Depends(get_video_history_service),
):
    svc.batch_update_histories(user.id, data.reports)
    return response.success()


@router.get('/list')
def get_history_list(
        video_id: int = Query(None),
        min_duration: int = Query(None),
        start_date: datetime = Query(None),
        end_date: datetime = Query(None),
        query: str = Query(None, description='搜索关键词'),
        nsfw: str = Query(None, description='NSFW筛选: all/yes/no'),
        site: str = Query(None, description='站点筛选'),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=200),
        user: User = Depends(get_current_user),
        svc: VideoHistoryService = Depends(get_video_history_service),
):
    filters = {
        'video_id': video_id,
        'min_duration': min_duration,
        'start_date': start_date,
        'end_date': end_date,
        'query': query,
        'nsfw': nsfw,
        'site': site,
    }
    video_histories = svc.list_histories(
        user_id=user.id,
        filters={k: v for k, v in filters.items() if v is not None},
        page=page,
        page_size=page_size,
    )
    return response.success(video_histories)


@router.post('/clear')
def clear_history(
        video_ids: list[int] = Body(None),
        user: dict = Depends(get_current_user),
        svc: VideoHistoryService = Depends(get_video_history_service),
):
    svc.clear_histories(
        user_id=user['id'],
        video_ids=video_ids,
    )
    return response.success()


@router.delete('/{history_id}')
def delete_history(
        history_id: int,
        user: User = Depends(get_current_user),
        svc: VideoHistoryService = Depends(get_video_history_service),
):
    deleted_count = svc.delete_history(user.id, history_id)
    if deleted_count == 0:
        return response.not_found('历史记录不存在')
    return response.success()
