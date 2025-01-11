from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy import select, func, or_, and_

from core.database import get_session
from models.links import SubscriptionVideo
from models.subscription import Subscription


def get_subscription_by_id(subscription_id: int):
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        return subscription


def list_subscriptions(
        query: Optional[str],
        content_type: Optional[str],
        page: int,
        page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    """获取订阅列表"""
    with get_session() as session:
        video_count_subquery = (
            select(
                SubscriptionVideo.subscription_id,
                func.count(SubscriptionVideo.video_id).label("video_count")
            )
            .group_by(SubscriptionVideo.subscription_id)
            .subquery()
        )

        statement = (
            select(
                Subscription,
                func.coalesce(video_count_subquery.c.video_count, 0).label("video_count")
            )
            .outerjoin(
                video_count_subquery,
                Subscription.id == video_count_subquery.c.subscription_id
            )
            .where(Subscription.is_deleted == 0)
        )

        filters = []
        if query:
            filters.append(
                or_(
                    Subscription.content_name.contains(query),
                    Subscription.description.contains(query)
                )
            )
        if content_type:
            filters.append(Subscription.content_type == content_type)

        if filters:
            statement = statement.where(and_(*filters))

        statement = statement.order_by(Subscription.created_at.desc())

        total = session.execute(
            select(Subscription.id)
            .where(Subscription.is_deleted == 0)
            .where(*filters)
        ).all()
        total_count = len(total)

        statement = statement.offset((page - 1) * page_size).limit(page_size)
        results = session.execute(statement).all()

        subscriptions = []
        for subscription, video_count in results:
            subscription_dict = subscription.to_dict()
            subscription_dict["total_extract"] = video_count
            subscriptions.append(subscription_dict)

        return subscriptions, total_count


def get_subscription_detail(subscription_id: int) -> Optional[Dict[str, Any]]:
    """获取订阅详情"""
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        return subscription.dict() if subscription else None


def update_subscription(
        subscription_id: int,
        update_data: Dict[str, Any]
) -> bool:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return False

        for key, value in update_data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        session.add(subscription)
        session.commit()
        return True


def toggle_status(subscription_id: int, status: bool, field: str) -> bool:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return False

        try:
            setattr(subscription, field, status)
            session.add(subscription)
            session.commit()
            return True
        except ValueError:
            return False
