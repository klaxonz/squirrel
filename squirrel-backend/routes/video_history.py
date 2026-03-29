from datetime import datetime
from typing import List
from fastapi import APIRouter, Query, Depends, Body
import common.response as response
from models.user import User
from schemas.video_history import (
    HistoryCreate
)
from services import video_history_service
from utils.jwt_helper import get_current_user

router = APIRouter(
    tags=['视频历史记录']
)


@router.post("/api/video-history/update")
def update_history(
        data: HistoryCreate,
        user: User = Depends(get_current_user)
):
    video_history_service.update_history(user.id, data)
    return response.success()


@router.get("/api/video-history/list")
def get_history_list(
        video_id: int = Query(None),
        min_duration: int = Query(None),
        start_date: datetime = Query(None),
        end_date: datetime = Query(None),
        query: str = Query(None, description='搜索关键词'),
        nsfw: str = Query(None, description="NSFW筛选: all/yes/no"),
        site: str = Query(None, description="站点筛选"),
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        user: User = Depends(get_current_user)
):
    filters = {
        "video_id": video_id,
        "min_duration": min_duration,
        "start_date": start_date,
        "end_date": end_date,
        "query": query,
        "nsfw": nsfw,
        "site": site
    }
    video_histories = video_history_service.list_histories(
        user_id=user.id,
        filters={k: v for k, v in filters.items() if v is not None},
        page=page,
        page_size=page_size
    )
    return response.success(video_histories)


@router.post("/api/video-history/clear")
def clear_history(
        video_ids: List[int] = Body(None),
        user: dict = Depends(get_current_user)
):
    video_history_service.clear_histories(
        user_id=user['id'],
        video_ids=video_ids
    )
    return response.success()


@router.delete("/api/video-history/{history_id}")
def delete_history(
        history_id: int,
        user: User = Depends(get_current_user)
):
    deleted_count = video_history_service.delete_history(user.id, history_id)
    if deleted_count == 0:
        return response.not_found('历史记录不存在')
    return response.success()
