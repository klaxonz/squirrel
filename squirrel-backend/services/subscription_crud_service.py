from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription


def get_subscription_by_id(subscription_id: int) -> Subscription:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        return subscription


def get_subscription_by_url_and_name(url: str, name: str) -> Subscription:
    with get_session() as session:
        subscription = session.scalars(select(Subscription).where(
            Subscription.url == url,
            Subscription.name == name
        )).first()
        return subscription


def get_active_user_subscription_by_url(user_id: int, url: str) -> Subscription:
    with get_session() as session:
        subscription = session.execute(
            select(Subscription)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.url == url,
                Subscription.is_deleted == False,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted == False,
            )
        ).scalar_one_or_none()
        return subscription


def get_active_user_subscription_url_map(user_id: int) -> Dict[str, int]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription.url, Subscription.id)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.is_deleted.is_(False),
                Subscription.url.is_not(None),
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
            )
        ).all()
        return {url: subscription_id for url, subscription_id in rows if url}


def get_deleted_user_subscription_urls(user_id: int) -> set[str]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription.url)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.url.is_not(None),
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(True),
            )
        ).all()
        return {url for url, in rows if url}


def check_subscription_status(user_id: int, url: str) -> Dict[str, Any]:
    if not url:
        return {
            'is_subscribed': False,
            'subscription_id': None,
        }
    with get_session() as session:
        subscription = session.scalars(
            select(Subscription).where(
                Subscription.url == url,
                Subscription.is_deleted.is_(False),
            )
        ).first()
        return {
            'is_subscribed': subscription is not None,
            'subscription_id': subscription.id if subscription else None,
        }


def get_user_subscription_nsfw(user_id: int, subscription_id: int) -> Optional[bool]:
    with get_session() as session:
        user_sub = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if user_sub:
            return user_sub.is_nsfw
        return None


def get_user_subscription_special_followed(user_id: int, subscription_id: int) -> Optional[bool]:
    with get_session() as session:
        user_sub = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if user_sub:
            return user_sub.is_special_followed
        return None


def verify_subscription_access(user_id: int, subscription_id: int) -> Tuple[Optional[Subscription], str]:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription or subscription.is_deleted:
            return None, "not_found"

        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if not user_subscription:
            return None, "forbidden"

        session.expunge(subscription)
        return subscription, "ok"


def update_subscription(
        subscription_id: int,
        update_data: Dict[str, Any]
) -> bool:
    import logging
    logger = logging.getLogger(__name__)
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return False

        for key, value in update_data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        session.add(subscription)
        session.commit()
        updated = True
    try:
        from services import search_suggestion_service
        search_suggestion_service.rebuild_users_for_subscription(subscription_id)
    except Exception as exc:
        logger.warning('Search suggestion subscription refresh skipped: %s', exc)
    return updated


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