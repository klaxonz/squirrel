import json
import logging
from typing import Dict, Any, List, Optional

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from models.message import Message
from models.subscription import Subscription, ContentType
from models.user import User
from services import user_video_feed_service
from services import subscription_sync_state_service
from services.subscription_crud_service import (
    get_subscription_by_url_and_name,
    get_subscription_by_id,
    get_active_user_subscription_url_map,
    get_deleted_user_subscription_urls,
)
from services.subscription_list_service import _resolve_subscription_nsfw
from services.subscription_runtime_models import SubscriptionMeta
from utils.url_helper import extract_top_level_domain
from common import constants
from queues.producer import RedisStreamProducer

logger = logging.getLogger(__name__)


def _detect_subscription_type(url: str) -> str:
    if 'youtube.com' in url or 'youtu.be' in url:
        if 'list=' in url or '/playlist?' in url:
            return ContentType.PLAYLIST

    if 'bilibili.com' in url:
        if '/favlist' in url or 'fid=' in url:
            return ContentType.PLAYLIST
        if '/season/' in url or 'season_id=' in url:
            return ContentType.PLAYLIST

    return ContentType.CHANNEL


def create_subscription(user_id: int, subscribe_info: SubscriptionMeta) -> Subscription:
    with get_session() as session:
        user_subscription = None
        subscription = get_subscription_by_url_and_name(url=subscribe_info.url, name=subscribe_info.name)
        if subscription:
            subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)
            return subscription
        else:
            content_type = _detect_subscription_type(subscribe_info.url)

            subscription = Subscription(
                type=content_type,
                name=subscribe_info.name,
                url=subscribe_info.url,
                avatar=subscribe_info.avatar,
                description=None,
                extra_data={}
            )
            session.add(subscription)
            session.flush()
        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription.id
            )).first()
        if not user_subscription:
            is_nsfw = _resolve_subscription_nsfw(subscribe_info.url)

            user_subscription = UserSubscription(
                user_id=user_id,
                subscription_id=subscription.id,
                is_nsfw=is_nsfw
            )
            session.add(user_subscription)
        session.commit()
    if user_subscription is not None:
        user_video_feed_service.backfill_user_subscription_feed(user_id, subscription.id, user_subscription.is_nsfw)
    subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)
    return subscription


def restore_subscription(subscription_id: int, user_id: int) -> None:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return

        subscription.is_deleted = False

        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.user_id == user_id
            )
        ).first()

        if user_subscription and user_subscription.is_deleted:
            user_subscription.is_deleted = False
        elif not user_subscription:
            user_subscription = UserSubscription(
                subscription_id=subscription_id,
                user_id=user_id,
                is_deleted=False,
                is_nsfw=False,
            )
            session.add(user_subscription)

        session.commit()
    user_video_feed_service.backfill_user_subscription_feed(user_id, subscription_id, user_subscription.is_nsfw)
    subscription = get_subscription_by_id(subscription_id)
    if subscription:
        subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)


def unsubscribe_by_id(user_id: int, subscription_id: int) -> bool:
    with get_session() as session:
        if not subscription_id:
            return False

        subscription = session.scalars(
            select(Subscription).where(Subscription.id == subscription_id)
        ).first()

        if not subscription:
            return False

        active_user_subscriptions = session.scalars(
            select(UserSubscription).where(
                UserSubscription.subscription_id == subscription.id,
                UserSubscription.is_deleted.is_(False),
            )
        ).all()

        for user_subscription in active_user_subscriptions:
            user_subscription.is_deleted = True

        subscription.is_deleted = True
        session.commit()

    user_video_feed_service.remove_subscription_feed(subscription_id)
    subscription_sync_state_service.deactivate_sync_states(
        subscription_id,
        reason='manual_unsubscribe',
    )

    return True


def toggle_nsfw_status(user_id: int, subscription_id: int, is_nsfw: bool) -> bool:
    with get_session() as session:
        user_sub = session.execute(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).scalar_one_or_none()
        if not user_sub:
            return False

        user_sub.is_nsfw = is_nsfw
        session.commit()
    user_video_feed_service.update_user_subscription_nsfw(user_id, subscription_id, is_nsfw)
    return True


def toggle_special_follow_status(user_id: int, subscription_id: int, is_special_followed: bool) -> bool:
    with get_session() as session:
        user_sub = session.execute(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).scalar_one_or_none()
        if not user_sub:
            return False

        user_sub.is_special_followed = is_special_followed
        session.commit()
    return True


def create_subscribe_message(url: str, user_id: int) -> Dict[str, Any]:
    with get_session() as session:
        task = {
            "url": url,
            "user_id": user_id
        }
        message = Message(body=json.dumps(task))
        session.add(message)
        session.commit()
        dump_json = message.to_dict()
        RedisStreamProducer().send(constants.QUEUE_SUBSCRIBE, dump_json)
    return dump_json


def list_user_ids() -> List[int]:
    with get_session() as session:
        rows = session.execute(select(User.id).order_by(User.id.asc())).all()
        return [user_id for user_id, in rows]