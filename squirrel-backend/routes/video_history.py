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
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        user: User = Depends(get_current_user)
):
    filters = {
        "video_id": video_id,
        "min_duration": min_duration,
        "start_date": start_date,
        "end_date": end_date
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
