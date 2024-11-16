from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from core.database import get_session
import common.response as response
from services.video_history_service import VideoHistoryService
from schemas.video_history import UpdateHistoryRequest, ClearHistoryRequest

router = APIRouter(
    tags=['视频历史记录']
)

@router.post("/api/video-history/update")
def update_watch_history(
    request: UpdateHistoryRequest,
    session: Session = Depends(get_session)
):
    """更新视频观看历史"""
    video_history_service = VideoHistoryService(session)
    video_history_service.update_watch_history(
        request.video_id,
        request.channel_id,
        request.watch_duration,
        request.last_position,
        request.total_duration
    )
    return response.success()

@router.get("/api/video-history/list")
def get_watch_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取观看历史列表"""
    video_history_service = VideoHistoryService()
    history_list, total = video_history_service.get_watch_history(page, page_size)
    return response.success({
        "items": history_list,
        "total": total,
        "page": page,
        "page_size": page_size
    })

@router.post("/api/video-history/clear")
def clear_history(
    request: ClearHistoryRequest
):
    """清空观看历史"""
    video_history_service = VideoHistoryService()
    video_history_service.clear_history(request.video_ids)
    return response.success() 