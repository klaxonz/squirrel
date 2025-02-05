from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.sql import text
from core.database import get_session
from dto.subscription_dto import SubscriptionDto
from meta.channel import SubscriptionMeta
from models.links import UserSubscription
from models.subscription import Subscription, ContentType
from sqlfile.subscription_sql import get_subscriptions_count_sql, get_subscriptions_sql, get_subscription_sql
from utils.sql_parser import parse_dynamic_sql


def get_subscription_by_id(subscription_id: int):
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        return subscription


def get_subscription_by_url_and_name(url: str, name: str):
    with get_session() as session:
        subscription = session.scalars(select(Subscription).where(
            Subscription.url == url,
            Subscription.name == name
        )).first()
        return subscription


def create_subscription(user_id: int, subscribe_info: SubscriptionMeta):
    with get_session() as session:
        subscription = get_subscription_by_url_and_name(url=subscribe_info.url, name=subscribe_info.name)
        if subscription:
            return subscription
        else:
            subscription = Subscription(
                type=ContentType.CHANNEL,
                name=subscribe_info.name,
                url=subscribe_info.url,
                avatar=subscribe_info.avatar,
                description=None,
                extra_data={}
            )
            session.add(subscription)
        user_subscription = session.scalars(
            select(UserSubscription).where(user_id=user_id, subscription_id=subscription.id)).first()
        if not user_subscription:
            user_subscription = UserSubscription(
                user_id=user_id,
                subscription_id=subscription.id
            )
            session.add(user_subscription)
        session.commit()
    return subscription


def list_subscriptions(
        user_id: int,
        query: Optional[str],
        type: Optional[str],
        page: int,
        page_size: int
) -> Tuple[List[Dict[str, Any]], int]:
    """Get subscription list"""
    with get_session() as session:
        params = {
            'user_id': user_id,
            'query': query,
            'type': type
        }
        
        count_sql = get_subscriptions_count_sql()
        dynamic_sql = parse_dynamic_sql(count_sql, params)
        total_count = session.execute(
            text(dynamic_sql),
            params
        ).scalar()
        
        sql = get_subscriptions_sql()
        final_sql = parse_dynamic_sql(sql, params)
        final_sql += " limit :limit offset :offset"
        params.update({
            'limit': page_size,
            'offset': (page - 1) * page_size
        })
        
        results = session.execute(text(final_sql), params).all()
        subscriptions = [SubscriptionDto.model_validate(row._mapping).model_dump() for row in results]
            
        return subscriptions, total_count


def get_subscription_detail(subscription_id: int) -> SubscriptionDto:
    with get_session() as session:
        sql = get_subscription_sql()
        params = {
            'subscription_id': subscription_id
        }
        parse_dynamic_sql(sql, params)
        subscription = session.execute(text(sql), params).first()
        if not subscription:
            return None
        subscription = SubscriptionDto.model_validate(subscription._mapping)
        return subscription


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
