from collections.abc import Callable
from typing import Any

from sqlalchemy import func, or_, select

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription, build_subscription_canonical_key
from infrastructure.database.session import get_session


class SubscriptionCrudService:
    def __init__(self, session_factory=get_session, invalidate_subscription: Callable[[int], None] | None = None):
        self.session_factory = session_factory
        self._invalidate_subscription = invalidate_subscription

    def get_subscription_by_id(self, subscription_id: int) -> Subscription:
        with self.session_factory() as session:
            subscription = session.get(Subscription, subscription_id)
            return subscription

    def get_subscription_by_url_and_name(self, url: str, name: str) -> Subscription:
        with self.session_factory() as session:
            subscription = session.scalars(
                select(Subscription).where(
                    Subscription.url == url,
                    Subscription.name == name,
                )
            ).first()
            return subscription

    def get_subscription_by_url(self, url: str) -> Subscription | None:
        canonical_key = build_subscription_canonical_key(url)
        with self.session_factory() as session:
            return session.scalars(
                select(Subscription)
                .where(or_(Subscription.canonical_key == canonical_key, Subscription.url == url))
                .order_by(Subscription.is_deleted.asc(), Subscription.id.asc()),
            ).first()

    def get_active_user_subscription_by_url(self, user_id: int, url: str) -> Subscription:
        with self.session_factory() as session:
            subscription = session.execute(
                select(Subscription)
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    Subscription.url == url,
                    Subscription.is_deleted.is_(False),
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).scalar_one_or_none()
            return subscription

    def get_active_user_subscription_url_map(self, user_id: int) -> dict[str, int]:
        with self.session_factory() as session:
            rows = session.execute(
                select(Subscription.url, Subscription.id)
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    Subscription.is_deleted.is_(False),
                    Subscription.url.is_not(None),
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).all()
            return {url: subscription_id for url, subscription_id in rows if url}

    def get_deleted_user_subscription_urls(self, user_id: int) -> set[str]:
        with self.session_factory() as session:
            rows = session.execute(
                select(Subscription.url)
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    Subscription.url.is_not(None),
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(True),
                ),
            ).all()
            return {url for (url,) in rows if url}

    def get_user_subscription_intent_versions(self, user_id: int, urls: list[str]) -> dict[str, int]:
        normalized_urls = list(dict.fromkeys(str(url).strip() for url in urls if str(url).strip()))
        if not normalized_urls:
            return {}
        with self.session_factory() as session:
            rows = session.execute(
                select(Subscription.url, func.max(UserSubscription.intent_version))
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    UserSubscription.user_id == user_id,
                    Subscription.url.in_(normalized_urls),
                )
                .group_by(Subscription.url),
            ).all()
        return {str(url): int(version or 0) for url, version in rows if url}

    def check_subscription_status(self, user_id: int, url: str) -> dict[str, Any]:
        if not url:
            return {
                'is_subscribed': False,
                'subscription_id': None,
            }
        with self.session_factory() as session:
            subscription = session.scalars(
                select(Subscription)
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    Subscription.url == url,
                    Subscription.is_deleted.is_(False),
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).first()
            return {
                'is_subscribed': subscription is not None,
                'subscription_id': subscription.id if subscription else None,
            }

    def get_user_subscription_nsfw(self, user_id: int, subscription_id: int) -> bool | None:
        with self.session_factory() as session:
            user_sub = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).first()
            if user_sub:
                return user_sub.is_nsfw
            return None

    def get_user_subscription_special_followed(self, user_id: int, subscription_id: int) -> bool | None:
        with self.session_factory() as session:
            user_sub = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).first()
            if user_sub:
                return user_sub.is_special_followed
            return None

    def verify_subscription_access(self, user_id: int, subscription_id: int) -> tuple[Subscription | None, str]:
        with self.session_factory() as session:
            subscription = session.get(Subscription, subscription_id)
            if not subscription or subscription.is_deleted:
                return None, 'not_found'

            user_subscription = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).first()
            if not user_subscription:
                return None, 'forbidden'

            session.expunge(subscription)
            return subscription, 'ok'

    def update_subscription(
        self,
        subscription_id: int,
        update_data: dict[str, Any],
    ) -> bool:
        with self.session_factory() as session:
            subscription = session.get(Subscription, subscription_id)
            if not subscription:
                return False

            for key, value in update_data.items():
                if hasattr(subscription, key):
                    setattr(subscription, key, value)

            session.add(subscription)
            session.commit()
        if self._invalidate_subscription is not None:
            self._invalidate_subscription(subscription_id)
        return True

    def toggle_status(self, subscription_id: int, status: bool, field: str) -> bool:
        with self.session_factory() as session:
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
