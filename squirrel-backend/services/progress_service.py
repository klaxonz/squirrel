"""
进度查询服务
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy import select, and_, func, desc

from core.database import get_session
from models.task.progress_record import ProgressRecord

logger = logging.getLogger()


def query_progress(
    trace_id: Optional[str] = None,
    subscription_id: Optional[int] = None,
    event_type: Optional[str] = None,
    scope: Optional[str] = "subscription",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[dict], int]:
    """
    查询进度记录
    
    Args:
        trace_id: 追踪ID
        subscription_id: 订阅ID
        event_type: 事件类型
        scope: 范围 - "subscription" 只返回订阅级别进度，"all" 返回所有进度
        start_time: 开始时间
        end_time: 结束时间
        page: 页码
        page_size: 每页数量
        
    Returns:
        进度记录列表和总数
    """
    with get_session() as session:
        conditions = []
        
        if trace_id:
            conditions.append(ProgressRecord.trace_id == trace_id)
        if subscription_id:
            conditions.append(ProgressRecord.subscription_id == subscription_id)
        if event_type:
            conditions.append(ProgressRecord.event_type == event_type)
        if start_time:
            conditions.append(ProgressRecord.created_at >= start_time)
        if end_time:
            conditions.append(ProgressRecord.created_at <= end_time)
        
        # 根据 scope 过滤事件类型
        if scope == "subscription":
            # 只返回订阅级别的进度，排除视频提取相关的进度
            conditions.append(
                ~ProgressRecord.event_type.like('video_extraction%')
            )
        
        base_query = select(ProgressRecord)
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # 获取总数
        count_query = select(func.count(ProgressRecord.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_count = session.execute(count_query).scalar() or 0
        
        # 分页查询
        records = session.scalars(
            base_query
            .order_by(desc(ProgressRecord.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        
        result = [record.to_dict() for record in records]
        return result, total_count


def get_latest_progress_by_trace_id(trace_id: str) -> Optional[dict]:
    """
    获取trace_id的最新进度
    
    Args:
        trace_id: 追踪ID
        
    Returns:
        最新进度记录
    """
    with get_session() as session:
        record = session.scalars(
            select(ProgressRecord)
            .where(ProgressRecord.trace_id == trace_id)
            .order_by(desc(ProgressRecord.created_at))
            .limit(1)
        ).first()
        
        return record.to_dict() if record else None


def get_progress_timeline(
    subscription_id: Optional[int] = None,
    trace_id: Optional[str] = None,
    limit: Optional[int] = 50
) -> List[dict]:
    """
    获取进度时间线
    
    Args:
        subscription_id: 订阅ID
        trace_id: 追踪ID
        limit: 限制数量，None 表示不限制
        
    Returns:
        进度时间线
    """
    with get_session() as session:
        conditions = []
        
        if subscription_id:
            conditions.append(ProgressRecord.subscription_id == subscription_id)
        if trace_id:
            conditions.append(ProgressRecord.trace_id == trace_id)
        
        query = select(ProgressRecord)
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(ProgressRecord.created_at)
        
        # 只有当 limit 不为 None 时才应用限制
        if limit is not None:
            query = query.limit(limit)
        
        records = session.scalars(query).all()
        
        return [record.to_dict() for record in records]


def get_progress_statistics(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> dict:
    """
    获取进度统计（仅订阅级别的进度，排除视频提取）
    
    Args:
        start_time: 开始时间
        end_time: 结束时间
        
    Returns:
        统计信息
    """
    with get_session() as session:
        conditions = []
        if start_time:
            conditions.append(ProgressRecord.created_at >= start_time)
        if end_time:
            conditions.append(ProgressRecord.created_at <= end_time)
        
        # 只统计订阅级别的进度，排除视频提取相关的进度
        conditions.append(~ProgressRecord.event_type.like('video_extraction%'))
        
        # 按事件类型统计
        event_stats = session.execute(
            select(
                ProgressRecord.event_type,
                func.count(ProgressRecord.id)
            )
            .where(and_(*conditions))
            .group_by(ProgressRecord.event_type)
        ).all()
        
        # 按订阅统计（Top 10）
        subscription_conditions = conditions + [ProgressRecord.subscription_id.isnot(None)]
        subscription_stats = session.execute(
            select(
                ProgressRecord.subscription_id,
                func.count(ProgressRecord.id)
            )
            .where(and_(*subscription_conditions))
            .group_by(ProgressRecord.subscription_id)
            .order_by(desc(func.count(ProgressRecord.id)))
            .limit(10)
        ).all()
        
        return {
            'event_type_stats': {event_type: count for event_type, count in event_stats},
            'top_subscriptions': [
                {'subscription_id': sub_id, 'count': count}
                for sub_id, count in subscription_stats
            ]
        }

