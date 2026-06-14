import logging
from collections.abc import Callable, Generator
from time import perf_counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import domains.user.application.services.config as user_config_service
from domains.video.application.services.engagement.clip_marker import serialize_marker as _default_serialize_marker
from domains.video.application.services.extraction.thumbnail_downloader import (
    thumbnail_downloader_service as _default_thumbnail_downloader,
)
from domains.video.application.services.listing.detail_loader import VideoDetailLoader
from domains.video.application.services.listing.page_loader import VideoListPageLoader
from domains.video.application.services.listing.profiles import merge_profiles as _merge_profiles
from domains.video.application.services.listing.profiles import video_extra_profiles as _video_extra_profiles
from domains.video.application.services.listing.query import (
    build_feed_rows_query as _default_build_feed_rows_query,
)
from domains.video.application.services.listing.query import (
    build_list_query as _default_build_list_query,
)
from domains.video.application.services.listing.query import (
    fetch_feed_page_video_ids as _default_fetch_feed_page_video_ids,
)
from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
from domains.video.domain.models.video import Video
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]

logger = logging.getLogger(__name__)


class VideoListService:
    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        get_user_config=None,
        serialize_marker=None,
        build_feed_rows_query=None,
        build_list_query=None,
        fetch_feed_page_video_ids=None,
        thumbnail_downloader=None,
        page_loader=None,
        detail_loader=None,
    ):
        self._session_factory = session_factory or _default_get_session
        self._get_user_config = get_user_config or user_config_service.get_config
        self._serialize_marker = serialize_marker or _default_serialize_marker
        self._build_feed_rows_query = build_feed_rows_query or _default_build_feed_rows_query
        self._build_list_query = build_list_query or _default_build_list_query
        self._fetch_feed_page_video_ids = fetch_feed_page_video_ids or _default_fetch_feed_page_video_ids
        self._thumbnail_downloader = thumbnail_downloader or _default_thumbnail_downloader
        self._page_loader = page_loader or VideoListPageLoader(self._thumbnail_downloader)
        self._detail_loader = detail_loader or VideoDetailLoader(
            thumbnail_downloader=self._thumbnail_downloader,
            serialize_marker=self._serialize_marker,
        )

    @staticmethod
    def _elapsed_ms(start_time: float) -> float:
        return round((perf_counter() - start_time) * 1000, 3)

    @staticmethod
    def _recall_video_ids(query: str | None) -> list[int] | None:
        """SEARCH_BACKEND=meilisearch 时用 Meilisearch 召回 video_id；否则返回 None 走 legacy。"""
        if not query or settings.SEARCH_BACKEND != 'meilisearch' or not settings.MEILISEARCH_URL:
            return None
        try:
            return get_meili_video_indexer().search(query)
        except Exception:
            logger.warning('meili search failed, fallback to legacy', exc_info=True)
            return None

    def list_videos(
        self,
        user_id: int,
        query: str,
        subscription_id: int,
        category: str,
        sort_by: str,
        nsfw: str,
        domains: list[str] | None,
        page: int,
        page_size: int,
        with_total: bool = False,
        time_range: str = "all",
        duration: str = "all",
        content_type: str = "all",
        special: str = "all",
    ) -> tuple[list[dict], int | None]:
        user_config = self._get_user_config(user_id)
        show_nsfw = user_config.get("showNsfw", False)
        offset = max((page - 1) * page_size, 0)
        started_at = perf_counter()

        with self._session_factory() as session:
            build_query_started_at = perf_counter()
            use_feed_row_pagination = (
                not query
                and duration == "all"
                and time_range == "all"
                and content_type == "all"
                and category in (None, "all", "preview")
            )
            if use_feed_row_pagination:
                base_ids_query = self._build_feed_rows_query(
                    user_id=user_id,
                    show_nsfw=show_nsfw,
                    subscription_id=subscription_id,
                    category=category,
                    sort_by=sort_by,
                    nsfw=nsfw,
                    domains=domains,
                    special=special,
                )
            else:
                recalled_ids = self._recall_video_ids(query)
                base_ids_query = self._build_list_query(
                    user_id=user_id,
                    show_nsfw=show_nsfw,
                    subscription_id=subscription_id,
                    query=query,
                    category=category,
                    sort_by=sort_by,
                    nsfw=nsfw,
                    domains=domains,
                    time_range=time_range,
                    duration=duration,
                    content_type=content_type,
                    special=special,
                    recalled_ids=recalled_ids,
                )
            build_query_ms = self._elapsed_ms(build_query_started_at)

            video_ids_started_at = perf_counter()
            if use_feed_row_pagination:
                video_ids = self._fetch_feed_page_video_ids(session, base_ids_query, offset=offset, page_size=page_size)
            else:
                video_ids = [
                    row.video_id
                    for row in session.execute(
                        base_ids_query.limit(page_size).offset(offset),
                    ).all()
                ]
            video_ids_ms = self._elapsed_ms(video_ids_started_at)

            total_count = None
            if with_total:
                total_count_started_at = perf_counter()
                count_source = base_ids_query.order_by(None).subquery()
                if use_feed_row_pagination:
                    total_count = (
                        session.execute(
                            select(func.count(func.distinct(count_source.c.video_id))).select_from(count_source),
                        ).scalar()
                        or 0
                    )
                else:
                    total_count = (
                        session.execute(
                            select(func.count()).select_from(count_source),
                        ).scalar()
                        or 0
                    )
                total_count_ms = self._elapsed_ms(total_count_started_at)
            else:
                total_count_ms = 0.0

            if not video_ids:
                logger.info(
                    "[Performance] list_videos user_id=%s category=%s page=%s page_size=%s query=%s nsfw=%s domains=%s "
                    "video_count=0 build_query_ms=%.3f video_ids_ms=%.3f total_count_ms=%.3f total_ms=%.3f",
                    user_id,
                    category,
                    page,
                    page_size,
                    bool(query),
                    nsfw,
                    len(domains or []),
                    build_query_ms,
                    video_ids_ms,
                    total_count_ms,
                    self._elapsed_ms(started_at),
                )
                return [], total_count

            page_items = self._page_loader.load_page(session, user_id=user_id, video_ids=video_ids)
            video_list = page_items.items
            page_timings = page_items.timings
            total_ms = self._elapsed_ms(started_at)

            logger.info(
                "[Performance] list_videos user_id=%s category=%s page=%s page_size=%s query=%s nsfw=%s domains=%s "
                "video_count=%s build_query_ms=%.3f video_ids_ms=%.3f total_count_ms=%.3f videos_ms=%.3f "
                "history_ms=%.3f subscriptions_ms=%.3f creators_ms=%.3f thumbnails_ms=%.3f assemble_ms=%.3f total_ms=%.3f",
                user_id,
                category,
                page,
                page_size,
                bool(query),
                nsfw,
                len(domains or []),
                len(video_list),
                build_query_ms,
                video_ids_ms,
                total_count_ms,
                page_timings['videos_ms'],
                page_timings['history_ms'],
                page_timings['subscriptions_ms'],
                page_timings['creators_ms'],
                page_timings['thumbnails_ms'],
                page_timings['assemble_ms'],
                total_ms,
            )

            return video_list, total_count

    def get_video(self, user_id: int, video_id: int) -> dict[str, Any] | None:
        with self._session_factory() as session:
            return self._detail_loader.load_detail(session, user_id=user_id, video_id=video_id)

    @staticmethod
    def video_extra_profiles(video: Video, key: str) -> list[dict]:
        return _video_extra_profiles(video, key)

    @staticmethod
    def merge_profiles(primary: list[dict], extra: list[dict]) -> list[dict]:
        return _merge_profiles(primary, extra)


video_list_service = VideoListService()
list_videos = video_list_service.list_videos
get_video = video_list_service.get_video
merge_profiles = video_list_service.merge_profiles
video_extra_profiles = video_list_service.video_extra_profiles
