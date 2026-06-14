from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.user.application.services.search.suggestions.formatting import serialize_rows, serialize_video_meta
from domains.user.application.services.search.suggestions.pools import match_rank
from domains.user.application.services.search.suggestions.predicates import apply_nsfw_visibility
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.junctions.video_creator import VideoCreator
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory


def list_video_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
        Video.is_deleted.is_(False),
        func.lower(Video.title).like(f'%{query}%'),
    ]
    apply_nsfw_visibility(conditions, effective_nsfw)

    rows = session.execute(
        select(
            Video.title.label('value'),
            Video.domain.label('meta'),
            match_rank(Video.title, query).label('match_rank'),
        )
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(*conditions)
        .order_by('match_rank', desc(Video.publish_date), desc(Video.created_at), desc(Video.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            'SuggestionRow',
            (),
            {
                'value': row.value,
                'meta': serialize_video_meta(row.meta),
            },
        )()
        for row in rows
    ]
    return serialize_rows(normalized_rows, 'video')[:limit]


def list_feed_video_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    """已订阅视频的前缀补全：实时 join（不再查 user_video_feed 投影表）。

    与 list_video_suggestions 同构，只是 nsfw 走 UserSubscription.is_nsfw（feed 语义）。
    """
    conditions: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
        Video.is_deleted.is_(False),
        func.lower(Video.title).like(f'%{query}%'),
    ]
    apply_nsfw_visibility(conditions, effective_nsfw)

    rows = session.execute(
        select(
            Video.title.label('value'),
            Video.domain.label('meta'),
            match_rank(Video.title, query).label('match_rank'),
        )
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(*conditions)
        .order_by('match_rank', desc(Video.publish_date), desc(Video.created_at), desc(Video.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            'SuggestionRow',
            (),
            {
                'value': row.value,
                'meta': serialize_video_meta(row.meta),
            },
        )()
        for row in rows
    ]
    return serialize_rows(normalized_rows, 'video')[:limit]


def list_subscription_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
        func.lower(Subscription.name).like(f'%{query}%'),
    ]
    apply_nsfw_visibility(conditions, effective_nsfw)

    rows = session.execute(
        select(
            Subscription.name.label('value'),
            Subscription.type.label('meta'),
            match_rank(Subscription.name, query).label('match_rank'),
            Subscription.updated_at.label('sort_time'),
            Subscription.id.label('sort_id'),
        )
        .select_from(UserSubscription)
        .join(Subscription, Subscription.id == UserSubscription.subscription_id)
        .where(*conditions)
        .order_by('match_rank', desc(Subscription.updated_at), desc(Subscription.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            'SuggestionRow',
            (),
            {
                'value': row.value,
                'meta': '频道' if str(row.meta or '').upper() == 'CHANNEL' else '订阅',
            },
        )()
        for row in rows
    ]
    return serialize_rows(normalized_rows, 'subscription')[:limit]


def list_creator_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
        Video.is_deleted.is_(False),
        Creator.is_deleted.is_(False),
        func.lower(Creator.name).like(f'%{query}%'),
    ]
    apply_nsfw_visibility(conditions, effective_nsfw)

    rows = session.execute(
        select(
            Creator.name.label('value'),
            match_rank(Creator.name, query).label('match_rank'),
            Video.publish_date.label('sort_time'),
            Creator.id.label('sort_id'),
        )
        .select_from(Creator)
        .join(VideoCreator, VideoCreator.creator_id == Creator.id)
        .join(Video, Video.id == VideoCreator.video_id)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(*conditions)
        .order_by('match_rank', desc(Video.publish_date), desc(Creator.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            'SuggestionRow',
            (),
            {
                'value': row.value,
                'meta': '创作者',
            },
        )()
        for row in rows
    ]
    return serialize_rows(normalized_rows, 'creator')[:limit]


def list_history_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        VideoHistory.user_id == user_id,
        Video.is_deleted.is_(False),
        func.lower(Video.title).like(f'%{query}%'),
    ]

    if effective_nsfw == 'blocked':
        return []

    if effective_nsfw in {'yes', 'no'}:
        nsfw_value = effective_nsfw == 'yes'
        conditions.append(
            UserSubscription.user_id == user_id,
        )
        conditions.append(
            UserSubscription.is_deleted.is_(False),
        )
        conditions.append(
            UserSubscription.is_nsfw.is_(nsfw_value),
        )

        rows = session.execute(
            select(
                Video.title.label('value'),
                match_rank(Video.title, query).label('match_rank'),
                VideoHistory.end_time.label('sort_time'),
                VideoHistory.id.label('sort_id'),
            )
            .select_from(VideoHistory)
            .join(Video, Video.id == VideoHistory.video_id)
            .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
            .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
            .where(*conditions)
            .order_by('match_rank', desc(VideoHistory.end_time), desc(VideoHistory.id))
            .limit(limit * 3),
        ).all()
    else:
        rows = session.execute(
            select(
                Video.title.label('value'),
                match_rank(Video.title, query).label('match_rank'),
                VideoHistory.end_time.label('sort_time'),
                VideoHistory.id.label('sort_id'),
            )
            .select_from(VideoHistory)
            .join(Video, Video.id == VideoHistory.video_id)
            .where(*conditions)
            .order_by('match_rank', desc(VideoHistory.end_time), desc(VideoHistory.id))
            .limit(limit * 3),
        ).all()

    normalized_rows = [
        type(
            'SuggestionRow',
            (),
            {
                'value': row.value,
                'meta': '最近看过',
            },
        )()
        for row in rows
    ]
    return serialize_rows(normalized_rows, 'history')[:limit]
