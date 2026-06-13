from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from sqlalchemy import and_, case, select
from sqlalchemy.orm import Session

from models.creator import Creator
from models.links import SubscriptionVideo, UserSubscription, VideoCreator
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from services.video.listing.profiles import merge_profiles, video_extra_profiles


@dataclass(frozen=True)
class VideoListPage:
    items: list[dict]
    timings: dict[str, float]


class VideoListPageLoader:
    def __init__(self, thumbnail_downloader):
        self.thumbnail_downloader = thumbnail_downloader

    @staticmethod
    def _elapsed_ms(start_time: float) -> float:
        return round((perf_counter() - start_time) * 1000, 3)

    def load_page(self, session: Session, *, user_id: int, video_ids: list[int]) -> VideoListPage:
        videos_started_at = perf_counter()
        order_case = case(
            {video_id: index for index, video_id in enumerate(video_ids)},
            value=Video.id,
        )
        videos = session.scalars(
            select(Video).where(Video.id.in_(video_ids)).order_by(order_case),
        ).all()
        video_map = {video.id: video for video in videos}
        videos_ms = self._elapsed_ms(videos_started_at)

        history_started_at = perf_counter()
        history_rows = session.execute(
            select(VideoHistory.video_id, VideoHistory.last_position).where(
                VideoHistory.user_id == user_id,
                VideoHistory.video_id.in_(video_ids),
            ),
        ).all()
        history_map = {row.video_id: row.last_position for row in history_rows}
        history_ms = self._elapsed_ms(history_started_at)

        subscriptions_started_at = perf_counter()
        subscriptions_map = self._load_subscription_profiles(session, user_id=user_id, video_ids=video_ids)
        subscriptions_ms = self._elapsed_ms(subscriptions_started_at)

        creators_started_at = perf_counter()
        actors_map = self._load_actor_profiles(session, video_ids=video_ids)
        creators_ms = self._elapsed_ms(creators_started_at)

        thumbnails_started_at = perf_counter()
        thumbnail_map = self.thumbnail_downloader.get_thumbnail_url_map(
            [
                (video.id, video.thumbnail, video.url)
                for video_id in video_ids
                for video in [video_map.get(video_id)]
                if video is not None
            ]
        )
        thumbnails_ms = self._elapsed_ms(thumbnails_started_at)

        assemble_started_at = perf_counter()
        video_list = []
        for video_id in video_ids:
            video = video_map.get(video_id)
            if not video:
                continue
            video_list.append({
                'id': video.id,
                'title': video.title,
                'url': video.url,
                'thumbnail': thumbnail_map.get(video.id),
                'duration': video.duration,
                'last_position': history_map.get(video.id, 0),
                'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
                'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'subscriptions': merge_profiles(
                    subscriptions_map.get(video.id, []),
                    video_extra_profiles(video, 'subscriptions'),
                ),
                'actors': merge_profiles(
                    actors_map.get(video.id, []),
                    video_extra_profiles(video, 'actors'),
                ),
            })
        assemble_ms = self._elapsed_ms(assemble_started_at)

        return VideoListPage(
            items=video_list,
            timings={
                'videos_ms': videos_ms,
                'history_ms': history_ms,
                'subscriptions_ms': subscriptions_ms,
                'creators_ms': creators_ms,
                'thumbnails_ms': thumbnails_ms,
                'assemble_ms': assemble_ms,
            },
        )

    @staticmethod
    def _load_subscription_profiles(session: Session, *, user_id: int, video_ids: list[int]) -> dict[int, list[dict]]:
        subscription_rows = session.execute(
            select(
                SubscriptionVideo.video_id,
                Subscription.id,
                Subscription.name,
                Subscription.url,
                Subscription.type,
                Subscription.avatar,
                UserSubscription.is_nsfw,
                UserSubscription.is_special_followed,
            )
            .select_from(SubscriptionVideo)
            .join(
                UserSubscription,
                and_(
                    UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            )
            .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
            .where(
                SubscriptionVideo.video_id.in_(video_ids),
                Subscription.is_deleted.is_(False),
            )
            .order_by(SubscriptionVideo.video_id.asc(), Subscription.id.asc()),
        ).all()
        subscriptions_map: dict[int, list[dict]] = {}
        seen_subscription_keys = set()
        for row in subscription_rows:
            key = (row.video_id, row.id)
            if key in seen_subscription_keys:
                continue
            seen_subscription_keys.add(key)
            subscriptions_map.setdefault(row.video_id, []).append(
                {
                    'id': row.id,
                    'name': row.name,
                    'url': row.url,
                    'type': row.type,
                    'avatar': row.avatar,
                    'is_nsfw': row.is_nsfw,
                    'is_special_followed': row.is_special_followed,
                }
            )
        return subscriptions_map

    @staticmethod
    def _load_actor_profiles(session: Session, *, video_ids: list[int]) -> dict[int, list[dict]]:
        creator_rows = session.execute(
            select(VideoCreator.video_id, Creator)
            .join(Creator, Creator.id == VideoCreator.creator_id)
            .where(
                VideoCreator.video_id.in_(video_ids),
                Creator.is_deleted.is_(False),
            )
            .order_by(VideoCreator.video_id.asc(), Creator.id.asc()),
        ).all()
        actors_map: dict[int, list[dict]] = {}
        for video_id, creator in creator_rows:
            actors_map.setdefault(video_id, []).append(creator.to_dict())
        return actors_map
