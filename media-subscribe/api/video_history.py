import json

from fastapi import APIRouter, Query

import common.response as response
from consumer import video_progress_task
from schemas.video_history import ClearHistoryRequest, UpdateHistoryRequest
from services.video_history_service import VideoHistoryService

router = APIRouter(
    tags=['视频历史记录']
)


@router.post("/api/video-history/update")
def update_watch_history(
        request: UpdateHistoryRequest,
):
    data = {
        'video_id': request.video_id,
        'channel_id': request.channel_id,
        'watch_duration': request.watch_duration,
        'last_position': request.last_position,
        'total_duration': request.total_duration
    }
    video_progress_task.process_video_progress_message.send(json.dumps(data))
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
