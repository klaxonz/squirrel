"""Featured video selection service.

Picks a small number of videos from the user's active subscriptions,
biased toward those with thumbnails for the home hero.
"""

import random
from collections.abc import Callable, Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.listing.page_loader import VideoListPageLoader
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]


def order_featured_video_ids(video_ids: list[int], *, stable: bool) -> list[int]:
    """Order a featured candidate pool for interactive or visual consumers."""
    ordered_ids = list(video_ids)
    if stable:
        return sorted(ordered_ids)
    random.shuffle(ordered_ids)
    return ordered_ids


class VideoFeaturedService:
    """Lightweight featured-pick service that returns a handful of videos
    for the home-page hero.  It does *not* use Meilisearch or
    the full ``VideoListService`` pipeline — it only needs a small
    random sample from the user's own subscription pool."""

    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        page_loader: VideoListPageLoader | None = None,
    ):
        self._session_factory = session_factory or _default_get_session
        self._page_loader = page_loader or VideoListPageLoader(
            thumbnail_downloader=None,  # replaced below
        )
        # Late-import to avoid circular dependency at module level
        from domains.video.application.services.extraction.thumbnail_downloader import (
            thumbnail_downloader_service,
        )
        if page_loader is None:
            self._page_loader = VideoListPageLoader(thumbnail_downloader_service)

    def get_featured_videos(self, user_id: int, count: int = 5, *, stable: bool = False) -> list[dict]:
        """Return up to *count* videos for the home hero.

        Selection strategy (no Meilisearch, PG-only):
        1. Collect all video ids from the user's active subscriptions.
        2. Shuffle and pick the first *count* that have thumbnails.
        3. Hydrate via ``VideoListPageLoader`` so the shape matches
           ``GET /api/video/list`` items exactly.
        """
        with self._session_factory() as session:
            # 1. Gather candidate video ids from active subscriptions
            sub_video_rows = session.execute(
                select(SubscriptionVideo.video_id)
                .join(
                    UserSubscription,
                    UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
                )
                .join(
                    Subscription,
                    Subscription.id == SubscriptionVideo.subscription_id,
                )
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                    Subscription.is_deleted.is_(False),
                )
                .distinct(),
            ).all()

            if not sub_video_rows:
                return []

            all_ids = order_featured_video_ids(
                [row.video_id for row in sub_video_rows],
                stable=stable,
            )

            # 2. Pick the first *count* that have thumbnails
            picked: list[int] = []
            # Batch-check thumbnails in chunks to avoid N+1
            chunk_size = 50
            for i in range(0, len(all_ids), chunk_size):
                chunk = all_ids[i : i + chunk_size]
                videos_with_thumb = session.scalars(
                    select(Video.id).where(
                        Video.id.in_(chunk),
                        Video.thumbnail.isnot(None),
                        Video.thumbnail != '',
                    ),
                ).all()
                # Preserve shuffle order
                thumb_set = set(videos_with_thumb)
                for vid in chunk:
                    if vid in thumb_set:
                        picked.append(vid)
                        if len(picked) >= count:
                            break
                if len(picked) >= count:
                    break

            if not picked:
                return []

            # 3. Hydrate
            page = self._page_loader.load_page(session, user_id=user_id, video_ids=picked)
            return page.items
