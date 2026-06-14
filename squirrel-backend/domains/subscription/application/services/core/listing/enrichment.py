from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.listing.serialization import serialize_datetime
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video_history import VideoHistory


def load_subscription_extract_counts(session: Session, subscription_ids: list[int]) -> dict[int, int]:
    if not subscription_ids:
        return {}

    rows = session.execute(
        select(
            SubscriptionVideo.subscription_id,
            func.count(SubscriptionVideo.video_id).label('total_extract'),
        )
        .where(SubscriptionVideo.subscription_id.in_(subscription_ids))
        .group_by(SubscriptionVideo.subscription_id),
    ).all()
    return {
        int(subscription_id): int(total_extract or 0)
        for subscription_id, total_extract in rows
    }


def load_subscription_unread_counts(session: Session, user_id: int, subscription_ids: list[int]) -> dict[int, int]:
    if not subscription_ids:
        return {}

    rows = session.execute(
        select(
            SubscriptionVideo.subscription_id,
            func.count(SubscriptionVideo.video_id).label('unread_count'),
        )
        .outerjoin(
            VideoHistory,
            and_(
                VideoHistory.video_id == SubscriptionVideo.video_id,
                VideoHistory.user_id == user_id,
            ),
        )
        .where(
            SubscriptionVideo.subscription_id.in_(subscription_ids),
            VideoHistory.video_id.is_(None),
        )
        .group_by(SubscriptionVideo.subscription_id),
    ).all()
    return {
        int(subscription_id): int(unread_count or 0)
        for subscription_id, unread_count in rows
    }


def load_recent_videos(session: Session, subscription_ids: list[int], limit: int = 10) -> dict[int, list[dict[str, Any]]]:
    if not subscription_ids:
        return {}

    from domains.video.domain.models.video import Video

    ranked_videos = (
        select(
            SubscriptionVideo.subscription_id.label('subscription_id'),
            Video.id.label('id'),
            Video.title.label('title'),
            Video.url.label('url'),
            Video.thumbnail.label('thumbnail'),
            Video.duration.label('duration'),
            Video.publish_date.label('publish_date'),
            func.row_number().over(
                partition_by=SubscriptionVideo.subscription_id,
                order_by=(Video.publish_date.desc().nullslast(), Video.created_at.desc()),
            ).label('rank'),
        )
        .select_from(SubscriptionVideo)
        .join(Video, Video.id == SubscriptionVideo.video_id)
        .where(
            SubscriptionVideo.subscription_id.in_(subscription_ids),
            Video.is_deleted.is_(False),
        )
        .subquery()
    )

    rows = session.execute(
        select(
            ranked_videos.c.subscription_id,
            ranked_videos.c.id,
            ranked_videos.c.title,
            ranked_videos.c.url,
            ranked_videos.c.thumbnail,
            ranked_videos.c.duration,
            ranked_videos.c.publish_date,
        )
        .where(ranked_videos.c.rank <= limit)
        .order_by(ranked_videos.c.subscription_id.asc(), ranked_videos.c.rank.asc()),
    ).all()

    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        sub_id = int(row.subscription_id)
        videos = grouped.setdefault(sub_id, [])
        videos.append({
            'id': int(row.id),
            'title': row.title or '',
            'url': row.url,
            'thumbnail': row.thumbnail,
            'duration': int(row.duration or 0),
            'publish_date': serialize_datetime(row.publish_date),
        })

    return grouped
