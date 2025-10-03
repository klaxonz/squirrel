import logging
from datetime import datetime
from typing import Optional

from fastapi import Query, APIRouter, Depends

from models.user import User
from utils.jwt_helper import get_current_user
import common.response as response
from services import message_service

logger = logging.getLogger()
router = APIRouter(tags=['消息追踪'])


@router.get("/api/message/trace/query")
def query_message_traces(
    trace_id: Optional[str] = Query(None, description="追踪ID"),
    queue_name: Optional[str] = Query(None, alias="queueName", description="队列名称"),
    message_type: Optional[str] = Query(None, alias="messageType", description="消息类型"),
    status: Optional[str] = Query(None, description="状态 (PENDING, SUCCESS, FAILED)"),
    start_time: Optional[str] = Query(None, alias="startTime", description="开始时间 ISO格式"),
    end_time: Optional[str] = Query(None, alias="endTime", description="结束时间 ISO格式"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="每页数量"),
    current_user: User = Depends(get_current_user)
):
    """
    查询消息追踪记录
    
    支持按 trace_id、队列名称、消息类型、状态、时间范围等条件过滤
    """
    try:
        # 解析时间参数
        start_dt = None
        end_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                return response.param_error("开始时间格式错误")
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except:
                return response.param_error("结束时间格式错误")
        
        messages, total_count = message_service.query_messages(
            trace_id=trace_id,
            queue_name=queue_name,
            message_type=message_type,
            status=status,
            start_time=start_dt,
            end_time=end_dt,
            page=page,
            page_size=page_size
        )
        
        return response.success({
            'messages': messages,
            'total': total_count,
            'page': page,
            'page_size': page_size
        })
    
    except Exception as e:
        logger.exception(f"Failed to query message traces: {e}")
        return response.server_error("查询消息追踪记录失败")


@router.get("/api/message/trace/detail")
def get_message_trace_detail(
    trace_id: str = Query(..., alias="traceId", description="追踪ID"),
    current_user: User = Depends(get_current_user)
):
    """获取指定 trace_id 的消息详情"""
    try:
        message = message_service.get_message_by_trace_id(trace_id)
        
        if not message:
            return response.not_found("未找到该追踪记录")
        
        import json
        try:
            body = json.loads(message.body) if message.body else {}
        except:
            body = {"_raw": message.body}
        
        result = {
            'id': message.id,
            'trace_id': message.trace_id,
            'queue_name': message.queue_name,
            'message_type': message.message_type,
            'body': body,
            'status': message.status,
            'error_msg': message.error_msg,
            'retry_count': message.retry_count,
            'processed_at': message.processed_at.isoformat() if message.processed_at else None,
            'created_at': message.created_at.isoformat() if message.created_at else None,
            'updated_at': message.updated_at.isoformat() if message.updated_at else None,
        }
        
        return response.success(result)
    
    except Exception as e:
        logger.exception(f"Failed to get message trace detail: {e}")
        return response.server_error("获取消息详情失败")


@router.get("/api/message/trace/statistics")
def get_message_statistics(
    start_time: Optional[str] = Query(None, alias="startTime", description="开始时间 ISO格式"),
    end_time: Optional[str] = Query(None, alias="endTime", description="结束时间 ISO格式"),
    current_user: User = Depends(get_current_user)
):
    """获取消息追踪统计信息"""
    try:
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                return response.param_error("开始时间格式错误")
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except:
                return response.param_error("结束时间格式错误")
        
        stats = message_service.get_message_statistics(
            start_time=start_dt,
            end_time=end_dt
        )
        
        return response.success(stats)
    
    except Exception as e:
        logger.exception(f"Failed to get message statistics: {e}")
        return response.server_error("获取统计信息失败")

