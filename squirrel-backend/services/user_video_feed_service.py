import logging
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.database import get_session
from models.links import SubscriptionVideo, UserSubscription
from models.user_video_feed import UserVideoFeed
from models.video import Video

logger = logging.getLogger(__name__)


def _upsert_feed_rows(session: Session, rows: list[dict]) -> None:
    if not rows:
        return

    bind = session.get_bind()
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "") or ""

    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    elif dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        raise RuntimeError(f"Unsupported database dialect for user_video_feed upsert: {dialect_name}")

    stmt = dialect_insert(UserVideoFeed).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "subscription_id", "video_id"],
        set_={
            "publish_date": stmt.excluded.publish_date,
            "video_created_at": stmt.excluded.video_created_at,
            "domain": stmt.excluded.domain,
            "is_nsfw": stmt.excluded.is_nsfw,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)


def _build_subscription_feed_rows(session: Session, user_id: int, subscription_id: int, is_nsfw: bool) -> list[dict]:
    rows = session.execute(
        select(
            SubscriptionVideo.subscription_id,
            SubscriptionVideo.video_id,
            Video.publish_date,
            Video.created_at,
            Video.domain,
        )
        .join(Video, Video.id == SubscriptionVideo.video_id)
        .where(
            SubscriptionVideo.subscription_id == subscription_id,
            Video.is_deleted.is_(False),
        ),
    ).all()

    now = datetime.now()
    return [
        {
            "user_id": user_id,
            "subscription_id": row.subscription_id,
            "video_id": row.video_id,
            "publish_date": row.publish_date,
            "video_created_at": row.created_at,
            "domain": row.domain,
            "is_nsfw": is_nsfw,
            "created_at": now,
            "updated_at": now,
        }
        for row in rows
    ]


def backfill_user_subscription_feed(user_id: int, subscription_id: int, is_nsfw: bool) -> None:
    with get_session() as session:
        session.execute(
            delete(UserVideoFeed).where(
                UserVideoFeed.user_id == user_id,
                UserVideoFeed.subscription_id == subscription_id,
            ),
        )
        _upsert_feed_rows(session, _build_subscription_feed_rows(session, user_id, subscription_id, is_nsfw))


def remove_user_subscription_feed(user_id: int, subscription_id: int) -> None:
    with get_session() as session:
        session.execute(
            delete(UserVideoFeed).where(
                UserVideoFeed.user_id == user_id,
                UserVideoFeed.subscription_id == subscription_id,
            ),
        )


def remove_subscription_feed(subscription_id: int) -> None:
    with get_session() as session:
        session.execute(
            delete(UserVideoFeed).where(
                UserVideoFeed.subscription_id == subscription_id,
            ),
        )


def update_user_subscription_nsfw(user_id: int, subscription_id: int, is_nsfw: bool) -> None:
    with get_session() as session:
        rows = session.scalars(
            select(UserVideoFeed).where(
                UserVideoFeed.user_id == user_id,
                UserVideoFeed.subscription_id == subscription_id,
            ),
        ).all()
        for row in rows:
            row.is_nsfw = is_nsfw


def add_video_to_active_subscribers(subscription_id: int, video_id: int) -> None:
    with get_session() as session:
        video = session.get(Video, video_id)
        if not video or video.is_deleted:
            return

        user_subscriptions = session.scalars(
            select(UserSubscription).where(
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False),
            ),
        ).all()
        if not user_subscriptions:
            return

        now = datetime.now()
        rows = [
            {
                "user_id": user_sub.user_id,
                "subscription_id": subscription_id,
                "video_id": video_id,
                "publish_date": video.publish_date,
                "video_created_at": video.created_at,
                "domain": video.domain,
                "is_nsfw": user_sub.is_nsfw,
                "created_at": now,
                "updated_at": now,
            }
            for user_sub in user_subscriptions
        ]
        _upsert_feed_rows(session, rows)


def refresh_video_feed_metadata(video_id: int) -> None:
    with get_session() as session:
        video = session.get(Video, video_id)
        if not video:
            return

        rows = session.scalars(
            select(UserVideoFeed).where(UserVideoFeed.video_id == video_id),
        ).all()
        for row in rows:
            row.publish_date = video.publish_date
            row.video_created_at = video.created_at
            row.domain = video.domain
