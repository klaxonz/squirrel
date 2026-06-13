from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import and_, exists, false, func, select
from sqlalchemy.sql.elements import ColumnElement

from models.links import UserSubscription
from models.subscription import Subscription
from models.user_video_feed import UserVideoFeed
from models.video import Video
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from services.search.query import escape_ilike
from services.video.moderation.nsfw_policy import resolve_effective_nsfw_filter


def contains_text(column: Any, term: str) -> ColumnElement[bool]:
    return column.ilike(f'%{escape_ilike(term)}%')


def normalize_domains(domains: list[str] | None) -> list[str]:
    if not domains:
        return []

    from utils import url_helper

    return [domain for domain in {url_helper.normalize_domain(item) for item in domains if item} if domain]


def feed_category_predicate(
    user_id: int,
    category: str,
    *,
    video_id_column: Any = Video.id,
    publish_date_column: Any = Video.publish_date,
) -> Any:
    published = and_(
        publish_date_column.is_not(None),
        publish_date_column <= func.now(),
    )

    if category == 'preview':
        return publish_date_column > func.now()
    if category == 'read':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == video_id_column,
                    ),
                ),
            ),
        )
    if category == 'unread':
        return and_(
            published,
            ~exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == video_id_column,
                    ),
                ),
            ),
        )
    if category == 'liked':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == video_id_column,
                        VideoInteraction.interaction_type == 1,
                    ),
                ),
            ),
        )
    if category == 'later':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == video_id_column,
                        VideoInteraction.interaction_type == 3,
                    ),
                ),
            ),
        )

    return published


def feed_time_range_predicates(time_range: str) -> list[Any]:
    if time_range == 'all':
        return []
    now = func.now()
    if time_range == 'today':
        return [UserVideoFeed.publish_date >= func.date(now)]
    if time_range == 'week':
        start = now - timedelta(days=now.extract('dow') - 1)
        return [UserVideoFeed.publish_date >= func.date(start)]
    if time_range == 'month':
        return [
            func.extract('year', UserVideoFeed.publish_date) == func.extract('year', now),
            func.extract('month', UserVideoFeed.publish_date) == func.extract('month', now),
        ]
    if time_range == 'year':
        return [func.extract('year', UserVideoFeed.publish_date) == func.extract('year', now)]
    return []


def build_active_subscriptions_query(
    *,
    user_id: int,
    subscription_id: int | None,
    nsfw: str,
    show_nsfw: bool,
    special: str,
    resolve_effective_nsfw_filter_func=resolve_effective_nsfw_filter,
) -> Any:
    effective_nsfw = resolve_effective_nsfw_filter_func(nsfw, show_nsfw)
    active_subscriptions = (
        select(
            UserSubscription.subscription_id.label('subscription_id'),
            UserSubscription.is_nsfw.label('is_nsfw'),
            UserSubscription.is_special_followed.label('is_special_followed'),
            Subscription.name.label('subscription_name'),
            Subscription.type.label('subscription_type'),
        )
        .select_from(UserSubscription)
        .join(Subscription, Subscription.id == UserSubscription.subscription_id)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
    )

    if subscription_id:
        active_subscriptions = active_subscriptions.where(UserSubscription.subscription_id == subscription_id)

    if effective_nsfw == 'blocked':
        active_subscriptions = active_subscriptions.where(false())
    elif effective_nsfw == 'yes':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_nsfw.is_(True))
    elif effective_nsfw == 'no':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_nsfw.is_(False))

    if special == 'yes':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_special_followed.is_(True))
    elif special == 'no':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_special_followed.is_(False))

    return active_subscriptions.subquery('active_subscriptions')
