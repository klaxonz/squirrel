"""
进度查询路由
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Query, Depends

from models.user import User
from utils.jwt_helper import get_current_user
import common.response as response
import services.progress_service as progress_service

logger = logging.getLogger()
router = APIRouter(tags=['进度跟踪'])


@router.get("/api/progress/list")
def list_progress(
    trace_id: Optional[str] = Query(None, description="追踪ID"),
    subscription_id: Optional[int] = Query(None, alias="subscriptionId", description="订阅ID"),
    event_type: Optional[str] = Query(None, alias="eventType", description="事件类型"),
    scope: Optional[str] = Query("subscription", description="范围：subscription(仅订阅级别) 或 all(全部)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=5000, alias="pageSize", description="每页数量"),
    current_user: User = Depends(get_current_user)
):
    """
    查询进度记录列表
    scope: subscription 只返回订阅级别的进度（排除video_extraction_*）
           all 返回所有进度
    """
    try:
        records, total_count = progress_service.query_progress(
            trace_id=trace_id,
            subscription_id=subscription_id,
            event_type=event_type,
            scope=scope,
            page=page,
            page_size=page_size
        )
        
        return response.success({
            'list': records,
            'total': total_count,
            'page': page,
            'page_size': page_size
        })
    
    except Exception as e:
        logger.error(f"Failed to query progress: {e}", exc_info=True)
        return response.server_error("查询进度失败")


@router.get("/api/progress/trace/{trace_id}/latest")
def get_trace_latest_progress(
    trace_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取trace_id的最新进度
    """
    try:
        record = progress_service.get_latest_progress_by_trace_id(trace_id)
        if not record:
            return response.not_found("未找到进度记录")
        
        return response.success(record)
    
    except Exception as e:
        logger.error(f"Failed to get latest progress: {e}", exc_info=True)
        return response.server_error("获取进度失败")


@router.get("/api/progress/timeline")
def get_progress_timeline(
    subscription_id: Optional[int] = Query(None, alias="subscriptionId", description="订阅ID"),
    trace_id: Optional[str] = Query(None, alias="traceId", description="追踪ID"),
    limit: Optional[int] = Query(50, ge=1, le=5000, description="限制数量，不传或传0表示不限制"),
    all: bool = Query(False, description="获取全部记录，不限制数量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取进度时间线
    all=true 时返回所有记录，否则受 limit 限制
    """
    try:
        if not subscription_id and not trace_id:
            return response.param_error("必须提供 subscription_id 或 trace_id")
        
        # 如果 all=true 或 limit=0，则不限制数量
        actual_limit = None if (all or limit == 0) else limit
        
        timeline = progress_service.get_progress_timeline(
            subscription_id=subscription_id,
            trace_id=trace_id,
            limit=actual_limit
        )
        
        return response.success(timeline)
    
    except Exception as e:
        logger.error(f"Failed to get progress timeline: {e}", exc_info=True)
        return response.server_error("获取时间线失败")


@router.get("/api/progress/statistics")
def get_progress_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    获取进度统计
    """
    try:
        stats = progress_service.get_progress_statistics()
        return response.success(stats)
    
    except Exception as e:
        logger.error(f"Failed to get progress statistics: {e}", exc_info=True)
        return response.server_error("获取统计信息失败")

