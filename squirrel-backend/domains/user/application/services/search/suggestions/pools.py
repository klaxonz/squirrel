from typing import Any

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.user.application.services.search.suggestions.formatting import dedupe_pool_items, serialize_video_meta
from domains.user.application.services.search.suggestions.predicates import subscription_visibility_predicates
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.junctions.video_creator import VideoCreator
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory

CREATOR_FEED_WINDOW = 1200

SOURCE_ORDERS = {
    'home': ('video', 'subscription', 'creator', 'history'),
    'subscribed': ('subscription', 'video', 'creator', 'history'),
    'history': ('history', 'video', 'subscription', 'creator'),
}


def match_rank(column: Any, query: str) -> Any:
    lowered_column = func.lower(func.coalesce(column, ''))
    return case(
        (lowered_column == query, 0),
        (lowered_column.like(f'{query}%'), 1),
        else_=2,
    )


def build_video_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    """已订阅视频 pool：实时 join（UserSubscription × SubscriptionVideo × Video）。"""
    rows = session.execute(
        select(
            Video.title.label('value'),
            Video.domain.label('meta'),
        )
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(
            Video.is_deleted.is_(False),
            *subscription_visibility_predicates(user_id, effective_nsfw),
        )
        .order_by(desc(Video.publish_date), desc(Video.created_at), desc(Video.id))
        .limit(limit),
    ).all()

    return dedupe_pool_items(
        {
            'type': 'video',
            'value': row.value,
            'label': row.value,
            'meta': serialize_video_meta(row.meta),
        }
        for row in rows
    )


def build_subscription_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    rows = session.execute(
        select(
            Subscription.name.label('value'),
            Subscription.type.label('meta'),
        )
        .select_from(UserSubscription)
        .join(Subscription, Subscription.id == UserSubscription.subscription_id)
        .where(*subscription_visibility_predicates(user_id, effective_nsfw))
        .order_by(desc(Subscription.updated_at), desc(Subscription.id))
        .limit(limit),
    ).all()

    return dedupe_pool_items(
        {
            'type': 'subscription',
            'value': row.value,
            'label': row.value,
            'meta': '频道' if str(row.meta or '').upper() == 'CHANNEL' else '订阅',
        }
        for row in rows
    )


def build_creator_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    """已订阅视频里的创作者 pool：先取最近 CREATOR_FEED_WINDOW 个已订阅视频，再 join creator。

    recent_feed 子查询改用实时 join（不再查 user_video_feed 投影表）。
    """
    recent_feed = (
        select(
            Video.id.label('video_id'),
            Video.publish_date.label('publish_date'),
            Video.created_at.label('video_created_at'),
        )
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(
            Video.is_deleted.is_(False),
            *subscription_visibility_predicates(user_id, effective_nsfw),
        )
        .order_by(desc(Video.publish_date), desc(Video.created_at), desc(Video.id))
        .limit(CREATOR_FEED_WINDOW)
        .subquery('recent_feed')
    )

    rows = session.execute(
        select(
            Creator.name.label('value'),
        )
        .select_from(recent_feed)
        .join(VideoCreator, VideoCreator.video_id == recent_feed.c.video_id)
        .join(Creator, Creator.id == VideoCreator.creator_id)
        .where(
            Creator.is_deleted.is_(False),
        )
        .order_by(desc(recent_feed.c.publish_date), desc(recent_feed.c.video_created_at), desc(Creator.id))
        .limit(limit),
    ).all()

    return dedupe_pool_items(
        {
            'type': 'creator',
            'value': row.value,
            'label': row.value,
            'meta': '创作者',
        }
        for row in rows
    )


def build_history_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    """观看历史 pool：nsfw 过滤改用实时 join（UserSubscription.is_nsfw）。"""
    if effective_nsfw == 'blocked':
        return []

    history_query = (
        select(
            Video.title.label('value'),
        )
        .select_from(VideoHistory)
        .join(Video, Video.id == VideoHistory.video_id)
        .where(
            VideoHistory.user_id == user_id,
            Video.is_deleted.is_(False),
        )
        .order_by(desc(VideoHistory.end_time), desc(VideoHistory.id))
        .limit(limit * 2)
    )

    if effective_nsfw in {'yes', 'no'}:
        nsfw_value = effective_nsfw == 'yes'
        rows = session.execute(
            history_query.join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
            .join(
                UserSubscription,
                UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
            )
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                UserSubscription.is_nsfw.is_(nsfw_value),
            ),
        ).all()
    else:
        rows = session.execute(history_query).all()

    return dedupe_pool_items(
        {
            'type': 'history',
            'value': row.value,
            'label': row.value,
            'meta': '最近看过',
        }
        for row in rows
    )
