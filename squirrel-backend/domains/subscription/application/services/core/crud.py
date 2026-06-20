from typing import Any

from sqlalchemy import select

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from infrastructure.database.session import get_session


class SubscriptionCrudService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

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

    def check_subscription_status(self, user_id: int, url: str) -> dict[str, Any]:
        if not url:
            return {
                'is_subscribed': False,
                'subscription_id': None,
            }
        with self.session_factory() as session:
            subscription = session.scalars(
                select(Subscription).where(
                    Subscription.url == url,
                    Subscription.is_deleted.is_(False),
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
            updated = True

        from domains.user.application.services.search.suggestion_service import (
            invalidate_users_for_subscription,
        )

        invalidate_users_for_subscription(subscription_id)
        return updated

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


subscription_crud_service = SubscriptionCrudService()
get_subscription_by_id = subscription_crud_service.get_subscription_by_id
get_subscription_by_url_and_name = subscription_crud_service.get_subscription_by_url_and_name
get_active_user_subscription_by_url = subscription_crud_service.get_active_user_subscription_by_url
get_active_user_subscription_url_map = subscription_crud_service.get_active_user_subscription_url_map
get_deleted_user_subscription_urls = subscription_crud_service.get_deleted_user_subscription_urls
check_subscription_status = subscription_crud_service.check_subscription_status
get_user_subscription_nsfw = subscription_crud_service.get_user_subscription_nsfw
get_user_subscription_special_followed = subscription_crud_service.get_user_subscription_special_followed
verify_subscription_access = subscription_crud_service.verify_subscription_access
update_subscription = subscription_crud_service.update_subscription
toggle_status = subscription_crud_service.toggle_status
