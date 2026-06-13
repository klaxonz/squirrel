from typing import Any

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session

from models.creator import Creator
from models.links import UserSubscription, VideoCreator
from models.subscription import Subscription
from models.user_video_feed import UserVideoFeed
from models.video import Video
from models.video_history import VideoHistory
from services.search.suggestions.formatting import dedupe_pool_items, serialize_video_meta
from services.search.suggestions.predicates import feed_visibility_predicates, subscription_visibility_predicates

DEFAULT_LIMIT = 8
MAX_LIMIT = 20
SUGGESTION_POOL_TTL_SECONDS = 120
SUGGESTION_POOL_MAX_ITEMS = 240
SUGGESTION_RESULT_TTL_SECONDS = 30
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
    rows = session.execute(
        select(
            Video.title.label('value'),
            UserVideoFeed.domain.label('meta'),
        )
        .select_from(UserVideoFeed)
        .join(Video, Video.id == UserVideoFeed.video_id)
        .where(
            Video.is_deleted.is_(False),
            *feed_visibility_predicates(user_id, effective_nsfw),
        )
        .order_by(desc(UserVideoFeed.publish_date), desc(UserVideoFeed.video_created_at), desc(Video.id))
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
    recent_feed = (
        select(
            UserVideoFeed.video_id,
            UserVideoFeed.publish_date,
            UserVideoFeed.video_created_at,
        )
        .select_from(UserVideoFeed)
        .where(*feed_visibility_predicates(user_id, effective_nsfw))
        .order_by(desc(UserVideoFeed.publish_date), desc(UserVideoFeed.video_created_at), desc(UserVideoFeed.video_id))
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

    rows = history_query
    if effective_nsfw in {'yes', 'no'}:
        rows = session.execute(
            history_query.join(UserVideoFeed, and_(
                UserVideoFeed.user_id == user_id,
                UserVideoFeed.video_id == VideoHistory.video_id,
                UserVideoFeed.is_nsfw.is_(effective_nsfw == 'yes'),
            )),
        ).all()
    else:
        rows = session.execute(rows).all()

    return dedupe_pool_items(
        {
            'type': 'history',
            'value': row.value,
            'label': row.value,
            'meta': '最近看过',
        }
        for row in rows
    )



