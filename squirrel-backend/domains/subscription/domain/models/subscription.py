from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING

from sqlalchemy import VARCHAR, Boolean, CheckConstraint, Index, Integer, Text, event
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship
from sqlalchemy.types import JSON

from infrastructure.database.base import Base

if TYPE_CHECKING:
    from domains.video.domain.junctions.subscription_video import SubscriptionVideo
    from domains.video.domain.models.video import Video
from domains.subscription.domain.junctions.user_subscription import UserSubscription


def build_subscription_canonical_key(url: str) -> str:
    return sha256(str(url).strip().encode('utf-8')).hexdigest()


def _canonical_key_for_url(url: str | None) -> str | None:
    return None if url is None else build_subscription_canonical_key(url)


def _video_links_join():
    from domains.video.domain.junctions.subscription_video import SubscriptionVideo

    return Subscription.id == foreign(SubscriptionVideo.subscription_id)


def _videos_secondary_join():
    from domains.video.domain.junctions.subscription_video import SubscriptionVideo
    from domains.video.domain.models.video import Video

    return Video.id == foreign(SubscriptionVideo.video_id)


def _user_subscriptions_join():
    from domains.subscription.domain.junctions.user_subscription import UserSubscription

    return Subscription.id == foreign(UserSubscription.subscription_id)


class ContentType:
    CHANNEL = 'CHANNEL'
    PLAYLIST = 'PLAYLIST'
    ACTRESS = 'ACTRESS'
    MOVIE = 'MOVIE'
    TV_SERIES = 'TV_SERIES'
    ACTOR = 'ACTOR'


class Subscription(Base):
    __tablename__ = 'subscription'

    __table_args__ = (
        Index('ix_subscription_is_deleted', 'is_deleted'),
        Index('ix_subscription_type', 'type'),
        Index('ix_subscription_deleted_id', 'is_deleted', 'id'),
        Index('uix_subscription_canonical_key', 'canonical_key', unique=True),
        CheckConstraint(
            '(url IS NULL AND canonical_key IS NULL) OR '
            '(url IS NOT NULL AND canonical_key IS NOT NULL)',
            name='ck_subscription_url_canonical_key_presence',
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    url: Mapped[str | None] = mapped_column(VARCHAR(2048), nullable=True)
    canonical_key: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    avatar: Mapped[str | None] = mapped_column(VARCHAR(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_videos: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    video_links: Mapped[list[SubscriptionVideo]] = relationship(
        'SubscriptionVideo',
        primaryjoin=_video_links_join,
        back_populates='subscription',
        viewonly=True,
    )
    videos: Mapped[list[Video]] = relationship(
        'Video',
        secondary='subscription_video',
        primaryjoin=_video_links_join,
        secondaryjoin=_videos_secondary_join,
        viewonly=True,
    )
    user_subscriptions: Mapped[list[UserSubscription]] = relationship(
        'UserSubscription',
        primaryjoin=_user_subscriptions_join,
        back_populates='subscription',
        viewonly=True,
    )


@event.listens_for(Subscription.url, 'set', retval=True)
def _sync_canonical_key_on_url_change(
    target: Subscription,
    value: str | None,
    _old_value: object,
    _initiator: object,
) -> str | None:
    target.canonical_key = _canonical_key_for_url(value)
    return value


@event.listens_for(Subscription, 'before_insert')
@event.listens_for(Subscription, 'before_update')
def _enforce_subscription_canonical_key(
    _mapper: object,
    _connection: object,
    target: Subscription,
) -> None:
    # The flush guard also corrects callers that explicitly supplied a stale derived value.
    target.canonical_key = _canonical_key_for_url(target.url)
