from typing import List
from sqlalchemy import func
from core.database import get_session
from models.video_history import VideoHistory
from schemas.video_history import HistoryCreate


def update_history(user_id: int, data: HistoryCreate):
    """
    更新观看记录（合并式更新）
    """
    with get_session() as session:
        # 查找最近24小时内的记录
        history = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id,
            VideoHistory.video_id == data.video_id
        ).first()

        if history:
            history.watch_duration += 0
            history.last_position = data.last_position
            history.end_time = func.now()
        else:
            history = VideoHistory(
                user_id=user_id,
                video_id=data.video_id,
                start_time=func.now(),
                end_time=func.now(),
                duration=0,
                watch_duration=0,
                last_position=data.last_position
            )
            session.add(history)

        session.commit()


def list_histories(user_id: int, filters: dict, page: int, page_size: int) -> dict:
    with get_session() as session:
        query = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id
        )

        # 应用过滤器
        if filters.get('video_id'):
            query = query.filter(VideoHistory.video_id == filters['video_id'])
        if filters.get('min_duration'):
            query = query.filter(VideoHistory.duration >= filters['min_duration'])
        if filters.get('start_date'):
            query = query.filter(VideoHistory.created_at >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(VideoHistory.created_at <= filters['end_date'])

        # 计算总数
        total = query.count()

        # 分页和排序
        items = query.order_by(VideoHistory.end_time.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return {
            "items": [item.to_dict() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size
        }


def clear_histories(user_id: int, video_ids: List[int] = None):
    """
    清除观看历史（支持批量）
    """
    with get_session() as session:
        query = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id
        )

        if video_ids:
            query = query.filter(VideoHistory.video_id.in_(video_ids))

        delete_count = query.delete()
        session.commit()
        return delete_count
