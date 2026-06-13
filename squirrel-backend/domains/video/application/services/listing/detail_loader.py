from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload, with_loader_criteria

import infrastructure.site_catalog.url as url_helper
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_clip_marker import VideoClipMarker
from domains.video.domain.models.video_history import VideoHistory
from domains.video.domain.models.video_interaction import VideoInteraction
from domains.video.application.services.listing.profiles import merge_profiles, video_extra_profiles


class VideoDetailLoader:
    def __init__(self, *, thumbnail_downloader, serialize_marker):
        self.thumbnail_downloader = thumbnail_downloader
        self.serialize_marker = serialize_marker

    def load_detail(self, session: Session, *, user_id: int, video_id: int) -> dict[str, Any] | None:
        video = session.scalars(
            select(Video)
            .where(Video.id == video_id)
            .options(
                selectinload(Video.subscription_links)
                .selectinload(SubscriptionVideo.subscription)
                .selectinload(Subscription.user_subscriptions),
                selectinload(Video.creators),
                selectinload(Video.histories),
                selectinload(Video.interactions),
            )
            .options(
                with_loader_criteria(
                    UserSubscription,
                    and_(
                        UserSubscription.user_id == user_id,
                        UserSubscription.is_deleted.is_(False),
                    ),
                    include_aliases=True,
                ),
                with_loader_criteria(
                    VideoHistory,
                    VideoHistory.user_id == user_id,
                    include_aliases=True,
                ),
                with_loader_criteria(
                    VideoInteraction,
                    VideoInteraction.user_id == user_id,
                    include_aliases=True,
                ),
            ),
        ).first()
        if not video:
            return None

        counts_map = self._load_subscription_video_counts(session, video)
        subscriptions_data = self._subscription_profiles(video, counts_map)
        video_history = max(video.histories, key=self._history_sort_key, default=None)
        video_interaction = max(video.interactions, key=self._interaction_sort_key, default=None)
        clip_markers = self._load_clip_markers(session, user_id=user_id, video_id=video_id)

        return {
            **video.to_dict(),
            'thumbnail': self.thumbnail_downloader.get_thumbnail_url(video.id, video.thumbnail, video.url),
            'interaction_type': video_interaction.interaction_type if video_interaction else None,
            'last_position': video_history.last_position if video_history else 0,
            'domain': url_helper.extract_top_level_domain(video.url),
            'subscriptions': merge_profiles(subscriptions_data, video_extra_profiles(video, 'subscriptions')),
            'actors': merge_profiles(
                [creator.to_dict() for creator in video.creators],
                video_extra_profiles(video, 'actors'),
            ),
            'creators': [creator.to_dict() for creator in video.creators],
            'clip_markers': [self.serialize_marker(marker) for marker in clip_markers],
        }

    @staticmethod
    def _load_subscription_video_counts(session: Session, video: Video) -> dict[int, int]:
        subscription_ids = {link.subscription_id for link in video.subscription_links}
        if not subscription_ids:
            return {}

        rows = session.execute(
            select(SubscriptionVideo.subscription_id, func.count(SubscriptionVideo.video_id).label('video_count'))
            .where(SubscriptionVideo.subscription_id.in_(list(subscription_ids)))
            .group_by(SubscriptionVideo.subscription_id),
        ).all()
        return {row[0]: row[1] for row in rows}

    @staticmethod
    def _subscription_profiles(video: Video, counts_map: dict[int, int]) -> list[dict]:
        subscriptions_data = []
        for link in video.subscription_links:
            subscription = link.subscription
            if not subscription:
                continue
            user_subscriptions = subscription.user_subscriptions or []
            if not user_subscriptions:
                continue
            user_subscription = user_subscriptions[0]
            subscription_data = subscription.to_dict()
            subscription_data['total_extract'] = counts_map.get(subscription.id, 0)
            subscription_data['total_videos'] = max(
                int(subscription_data.get('total_videos') or 0),
                subscription_data['total_extract'],
            )
            subscription_data['is_nsfw'] = user_subscription.is_nsfw
            subscriptions_data.append(subscription_data)
        return subscriptions_data

    @staticmethod
    def _load_clip_markers(session: Session, *, user_id: int, video_id: int) -> list[VideoClipMarker]:
        return list(
            session.scalars(
                select(VideoClipMarker)
                .where(
                    VideoClipMarker.user_id == user_id,
                    VideoClipMarker.video_id == video_id,
                )
                .order_by(VideoClipMarker.start_time.asc(), VideoClipMarker.created_at.asc(), VideoClipMarker.id.asc()),
            ).all()
        )

    @staticmethod
    def _history_sort_key(history: VideoHistory) -> Any:
        return history.updated_at or history.end_time or history.created_at

    @staticmethod
    def _interaction_sort_key(interaction: VideoInteraction) -> Any:
        return interaction.updated_at or interaction.created_at
