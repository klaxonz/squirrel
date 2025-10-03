import json
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, and_, or_, func, desc

from core.database import get_session
from models.message import Message


def create_message(content: dict) -> Message:
    with get_session() as session:
        message = Message()
        message.body = json.dumps(content)
        session.add(message)
        session.commit()
        return message


def record_message_trace(
    trace_id: str,
    queue_name: str,
    message_type: Optional[str],
    body: dict,
    status: str = 'PENDING'
) -> Message:
    with get_session() as session:
        message = Message()
        message.trace_id = trace_id
        message.queue_name = queue_name
        message.message_type = message_type
        message.body = json.dumps(body, ensure_ascii=False)
        message.status = status
        session.add(message)
        session.commit()
        return message


def update_message_status(
    trace_id: str,
    status: str,
    error_msg: Optional[str] = None,
    processed_at: Optional[datetime] = None
) -> None:
    with get_session() as session:
        message = session.scalars(
            select(Message).where(Message.trace_id == trace_id)
        ).first()
        
        if message:
            message.status = status
            if error_msg:
                message.error_msg = error_msg
            if processed_at:
                message.processed_at = processed_at
            elif status == 'SUCCESS':
                message.processed_at = datetime.now()
            session.commit()


def get_message_by_trace_id(trace_id: str) -> Optional[Message]:
    with get_session() as session:
        message = session.scalars(
            select(Message).where(Message.trace_id == trace_id)
        ).first()
        return message


def query_messages(
    trace_id: Optional[str] = None,
    queue_name: Optional[str] = None,
    message_type: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[List[dict], int]:
    with get_session() as session:
        conditions = []
        
        if trace_id:
            conditions.append(Message.trace_id == trace_id)
        if queue_name:
            conditions.append(Message.queue_name == queue_name)
        if message_type:
            conditions.append(Message.message_type == message_type)
        if status:
            conditions.append(Message.status == status)
        if start_time:
            conditions.append(Message.created_at >= start_time)
        if end_time:
            conditions.append(Message.created_at <= end_time)
        
        base_query = select(Message)
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # 获取总数
        count_query = select(func.count(Message.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_count = session.execute(count_query).scalar() or 0
        
        # 分页查询
        messages = session.scalars(
            base_query
            .order_by(desc(Message.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        
        result = []
        for msg in messages:
            try:
                body = json.loads(msg.body) if msg.body else {}
            except:
                body = {"_raw": msg.body}
            
            result.append({
                'id': msg.id,
                'trace_id': msg.trace_id,
                'queue_name': msg.queue_name,
                'message_type': msg.message_type,
                'body': body,
                'status': msg.status,
                'error_msg': msg.error_msg,
                'retry_count': msg.retry_count,
                'processed_at': msg.processed_at.isoformat() if msg.processed_at else None,
                'created_at': msg.created_at.isoformat() if msg.created_at else None,
                'updated_at': msg.updated_at.isoformat() if msg.updated_at else None,
            })
        
        return result, total_count


def get_message_statistics(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> dict:
    with get_session() as session:
        conditions = []
        if start_time:
            conditions.append(Message.created_at >= start_time)
        if end_time:
            conditions.append(Message.created_at <= end_time)
        
        base_query = select(Message)
        if conditions:
            base_query = base_query.where(and_(*conditions))
        
        # 按状态统计
        status_stats = session.execute(
            select(Message.status, func.count(Message.id))
            .where(and_(*conditions) if conditions else True)
            .group_by(Message.status)
        ).all()
        
        # 按队列统计
        queue_stats = session.execute(
            select(Message.queue_name, func.count(Message.id))
            .where(and_(*conditions) if conditions else True)
            .group_by(Message.queue_name)
            .order_by(desc(func.count(Message.id)))
            .limit(10)
        ).all()
        
        return {
            'status_stats': {status: count for status, count in status_stats},
            'queue_stats': {queue: count for queue, count in queue_stats if queue}
        }
