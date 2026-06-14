import base64
import logging
from collections.abc import Callable, Generator
from time import perf_counter
from typing import Any

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
    fetch_user_state_id_set,
    fetch_user_state_video_ids,
    filter_recalled_ids,
    recall_offset_ids,
)
from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
from domains.video.domain.models.video import Video
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]

logger = logging.getLogger(__name__)

# 浏览 keyset 补页：单轮召回倍数（给 PG 权限/category 过滤留缓冲）
_RECALL_BUFFER_FACTOR = 2
# 补页最大轮次（防 liked 等低命中率 category 无限召回）
_MAX_RECALL_ROUNDS = 5
# 搜索场景 OFFSET 的 Meili 召回上限（覆盖深度搜索分页需求）
_SEARCH_RECALL_LIMIT = 5000


def _encode_page_cursor(page: int) -> str:
    """搜索场景把 page 编码成 base64 cursor（复用 cursor 字段，前端无需区分场景）。"""
    return base64.urlsafe_b64encode(str(page).encode()).decode().rstrip('=')


def _decode_page_cursor(cursor: str) -> int:
    """解码搜索场景的 page cursor；非法返回 1。"""
    try:
        padded = cursor + '=' * (-len(cursor) % 4)
        return int(base64.urlsafe_b64decode(padded.encode()).decode())
    except (ValueError, TypeError):
        return 1


class VideoListService:
    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        get_user_config=None,
        serialize_marker=None,
        thumbnail_downloader=None,
        page_loader=None,
        detail_loader=None,
    ):
        self._session_factory = session_factory or _default_get_session
        self._get_user_config = get_user_config or user_config_service.get_config
        self._serialize_marker = serialize_marker or _default_serialize_marker
        self._thumbnail_downloader = thumbnail_downloader or _default_thumbnail_downloader
        self._page_loader = page_loader or VideoListPageLoader(self._thumbnail_downloader)
        self._detail_loader = detail_loader or VideoDetailLoader(
            thumbnail_downloader=self._thumbnail_downloader,
            serialize_marker=self._serialize_marker,
        )

    @staticmethod
    def _elapsed_ms(start_time: float) -> float:
        return round((perf_counter() - start_time) * 1000, 3)

    def list_videos(
        self,
        user_id: int,
        query: str,
        subscription_id: int,
        category: str,
        sort_by: str,
        nsfw: str,
        domains: list[str] | None,
        cursor: str | None,
        page_size: int,
        time_range: str = "all",
        duration: str = "all",
        content_type: str = "all",
        special: str = "all",
    ) -> tuple[list[dict], str | None]:
        """列表查询。返回 (videos, next_cursor)；next_cursor 为 None 表示无更多。

        分两条路径：
        - 浏览（无搜索词）：keyset 游标分页，Meili 按页召回 + PG 过滤，不足补页
        - 搜索（有搜索词）：Meili 召回全集(≤5000) + PG 过滤 + OFFSET 分页
        """
        user_config = self._get_user_config(user_id)
        show_nsfw = user_config.get("showNsfw", False)
        started_at = perf_counter()

        has_query = bool(query and query.strip())
        with self._session_factory() as session:
            if has_query:
                videos, next_cursor, timings = self._list_search_offset(
                    session,
                    user_id=user_id,
                    show_nsfw=show_nsfw,
                    query=query,
                    subscription_id=subscription_id,
                    category=category,
                    sort_by=sort_by,
                    nsfw=nsfw,
                    domains=domains,
                    cursor=cursor,
                    page_size=page_size,
                    time_range=time_range,
                    duration=duration,
                    content_type=content_type,
                    special=special,
                )
            else:
                videos, next_cursor, timings = self._list_browse_keyset(
                    session,
                    user_id=user_id,
                    show_nsfw=show_nsfw,
                    subscription_id=subscription_id,
                    category=category,
                    sort_by=sort_by,
                    nsfw=nsfw,
                    domains=domains,
                    cursor=cursor,
                    page_size=page_size,
                    time_range=time_range,
                    duration=duration,
                    content_type=content_type,
                    special=special,
                )

        logger.info(
            "[Performance] list_videos user_id=%s category=%s query=%s page_size=%s "
            "video_count=%s recall_ms=%.3f filter_ms=%.3f page_ms=%.3f total_ms=%.3f next_cursor=%s",
            user_id, category, has_query, page_size, len(videos),
            timings['recall_ms'], timings['filter_ms'], timings['page_ms'],
            self._elapsed_ms(started_at), bool(next_cursor),
        )
        return videos, next_cursor

    def _list_browse_keyset(
        self, session: Session, *, user_id: int, show_nsfw: bool, subscription_id: int | None,
        category: str, sort_by: str, nsfw: str, domains: list[str] | None,
        cursor: str | None, page_size: int, time_range: str, duration: str,
        content_type: str, special: str,
    ) -> tuple[list[dict], str | None, dict[str, float]]:
        """浏览 keyset：循环召回 + PG 过滤，补足一页。

        每轮：Meili.recall_page(cursor, limit=page_size*2) → PG filter_recalled_ids
        → 累积到 ≥page_size 或 Meili 到底或达 _MAX_RECALL_ROUNDS。
        """
        # read/liked/later 走 PG 直查（per-user 表 keyset），不走 Meili keyset
        if category in ('read', 'liked', 'later'):
            return self._list_user_state_browse(
                session,
                user_id=user_id, show_nsfw=show_nsfw, subscription_id=subscription_id,
                category=category, nsfw=nsfw, domains=domains, cursor=cursor,
                page_size=page_size, time_range=time_range, duration=duration,
                content_type=content_type, special=special,
            )

        empty_timings = {'recall_ms': 0.0, 'filter_ms': 0.0, 'page_ms': 0.0}
        if not settings.MEILISEARCH_URL:
            logger.warning('browse requested but MEILISEARCH_URL not set -- returning empty')
            return [], None, empty_timings

        indexer = get_meili_video_indexer()
        collected_video_ids: list[int] = []
        last_cursor = cursor
        exhausted = False
        total_recall_ms = 0.0
        total_filter_ms = 0.0

        for _round in range(_MAX_RECALL_ROUNDS):
            if len(collected_video_ids) >= page_size:
                break
            recall_limit = max(page_size * _RECALL_BUFFER_FACTOR, 20)

            recall_started = perf_counter()
            try:
                recalled_ids, next_cursor = indexer.recall_page(
                    domains=domains, time_range=time_range, duration=duration,
                    cursor=last_cursor, limit=recall_limit,
                )
            except Exception:
                logger.warning('meili recall_page failed', exc_info=True)
                return [], None, {'recall_ms': total_recall_ms, 'filter_ms': total_filter_ms, 'page_ms': 0.0}
            total_recall_ms += self._elapsed_ms(recall_started)

            if next_cursor is None:
                exhausted = True
            else:
                last_cursor = next_cursor

            if not recalled_ids:
                exhausted = True
                break

            # PG 过滤本轮召回（权限 + category）
            filter_started = perf_counter()
            filtered_ids = filter_recalled_ids(
                session,
                recalled_ids=recalled_ids,
                user_id=user_id,
                show_nsfw=show_nsfw,
                subscription_id=subscription_id,
                category=category,
                nsfw=nsfw,
                content_type=content_type,
                special=special,
            )
            total_filter_ms += self._elapsed_ms(filter_started)

            for vid in filtered_ids:
                if vid not in collected_video_ids:
                    collected_video_ids.append(vid)
                    if len(collected_video_ids) >= page_size:
                        break

            if exhausted:
                break

        # 是否还有下一页：只看 Meili 是否还有更多（last_cursor 非 None）。
        # 不依赖 collected 数量——collected 不足 page_size 只说明本页较小（category 命中率低），
        # 不代表 Meili 没数据了。若 Meili 已到底（exhausted），last_cursor 为 None。
        has_more = last_cursor is not None
        page_cursor = last_cursor if has_more else None

        # 只取 page_size 个，hydration
        page_ids = collected_video_ids[:page_size]
        if not page_ids:
            return [], None, {'recall_ms': total_recall_ms, 'filter_ms': total_filter_ms, 'page_ms': 0.0}
        page_started = perf_counter()
        page_items = self._page_loader.load_page(session, user_id=user_id, video_ids=page_ids)
        page_ms = self._elapsed_ms(page_started)
        return page_items.items, page_cursor, {'recall_ms': total_recall_ms, 'filter_ms': total_filter_ms, 'page_ms': page_ms}

    def _list_search_offset(
        self, session: Session, *, user_id: int, show_nsfw: bool, query: str,
        subscription_id: int | None, category: str, sort_by: str, nsfw: str,
        domains: list[str] | None, cursor: str | None, page_size: int,
        time_range: str, duration: str, content_type: str, special: str,
    ) -> tuple[list[dict], str | None, dict[str, float]]:
        """搜索 OFFSET：Meili 召回全集(≤5000) → PG 过滤 → OFFSET 分页。

        cursor 在搜索场景编码 page 值（复用 cursor 字段，前端无需区分场景）。
        """
        # read/liked/later 搜索：PG 取 id 集合 → Meili filter id IN [...] 反向交集
        if category in ('read', 'liked', 'later'):
            return self._list_user_state_search(
                session,
                user_id=user_id, show_nsfw=show_nsfw, query=query,
                subscription_id=subscription_id, category=category, nsfw=nsfw,
                domains=domains, cursor=cursor, page_size=page_size,
                time_range=time_range, duration=duration,
                content_type=content_type, special=special,
            )

        empty_timings = {'recall_ms': 0.0, 'filter_ms': 0.0, 'page_ms': 0.0}
        page = _decode_page_cursor(cursor) if cursor else 1
        offset = max((page - 1) * page_size, 0)

        if not settings.MEILISEARCH_URL:
            logger.warning('search requested but MEILISEARCH_URL not set -- returning empty')
            return [], None, empty_timings

        recall_started = perf_counter()
        try:
            recalled_ids = recall_offset_ids(
                query=query,
                domains=domains,
                time_range=time_range,
                duration=duration,
                limit=_SEARCH_RECALL_LIMIT,
            )
        except Exception:
            logger.warning('meili recall failed', exc_info=True)
            return [], None, {'recall_ms': self._elapsed_ms(recall_started), 'filter_ms': 0.0, 'page_ms': 0.0}
        recall_ms = self._elapsed_ms(recall_started)

        if not recalled_ids:
            return [], None, {'recall_ms': recall_ms, 'filter_ms': 0.0, 'page_ms': 0.0}

        filter_started = perf_counter()
        filtered_ids = filter_recalled_ids(
            session,
            recalled_ids=recalled_ids,
            user_id=user_id,
            show_nsfw=show_nsfw,
            subscription_id=subscription_id,
            category=category,
            nsfw=nsfw,
            content_type=content_type,
            special=special,
        )
        filter_ms = self._elapsed_ms(filter_started)

        # OFFSET 分页
        page_ids = filtered_ids[offset:offset + page_size]
        has_more = offset + page_size < len(filtered_ids)
        next_cursor = _encode_page_cursor(page + 1) if has_more else None

        if not page_ids:
            return [], None, {'recall_ms': recall_ms, 'filter_ms': filter_ms, 'page_ms': 0.0}

        page_started = perf_counter()
        page_items = self._page_loader.load_page(session, user_id=user_id, video_ids=page_ids)
        page_ms = self._elapsed_ms(page_started)
        return page_items.items, next_cursor, {'recall_ms': recall_ms, 'filter_ms': filter_ms, 'page_ms': page_ms}

    def _list_user_state_browse(
        self, session: Session, *, user_id: int, show_nsfw: bool, subscription_id: int | None,
        category: str, nsfw: str, domains: list[str] | None, cursor: str | None,
        page_size: int, time_range: str, duration: str, content_type: str, special: str,
    ) -> tuple[list[dict], str | None, dict[str, float]]:
        """read/liked/later 浏览：PG per-user 表 keyset 直查 + 权限过滤。

        - 不调 Meili（这些 category 的语义是"最近交互的"，按交互时间排序）
        - PG keyset: read 按 end_time，liked/later 按 interaction.created_at
        - 取出 video_ids 后走 filter_recalled_ids 做权限(订阅/nsfw/special/content_type)过滤
        """
        empty_timings = {'recall_ms': 0.0, 'filter_ms': 0.0, 'page_ms': 0.0}
        # 多取一些缓冲，给权限过滤留余量
        fetch_limit = max(page_size * _RECALL_BUFFER_FACTOR, 20)

        recall_started = perf_counter()
        try:
            video_ids, next_cursor = fetch_user_state_video_ids(
                session, user_id=user_id, category=category,
                cursor=cursor, limit=fetch_limit,
            )
        except Exception:
            logger.warning('fetch_user_state_video_ids failed', exc_info=True)
            return [], None, empty_timings
        recall_ms = self._elapsed_ms(recall_started)

        if not video_ids:
            return [], None, {'recall_ms': recall_ms, 'filter_ms': 0.0, 'page_ms': 0.0}

        filter_started = perf_counter()
        # 权限过滤；category 传 'all'（per-user 表已保证 category 语义，不再 EXISTS）
        filtered_ids = filter_recalled_ids(
            session,
            recalled_ids=video_ids,
            user_id=user_id, show_nsfw=show_nsfw, subscription_id=subscription_id,
            category='all', nsfw=nsfw, content_type=content_type, special=special,
        )
        filter_ms = self._elapsed_ms(filter_started)

        # 取 page_size 个；权限过滤后可能不足一页（用户解绑了部分订阅）
        page_ids = filtered_ids[:page_size]
        # has_more 看 PG per-user 表是否还有更多（next_cursor 非 None）
        # 注意：即使权限过滤后不足一页，只要 per-user 表还有更多，就允许翻页
        page_cursor = next_cursor

        if not page_ids:
            return [], page_cursor, {'recall_ms': recall_ms, 'filter_ms': filter_ms, 'page_ms': 0.0}

        page_started = perf_counter()
        page_items = self._page_loader.load_page(session, user_id=user_id, video_ids=page_ids)
        page_ms = self._elapsed_ms(page_started)
        return page_items.items, page_cursor, {'recall_ms': recall_ms, 'filter_ms': filter_ms, 'page_ms': page_ms}

    def _list_user_state_search(
        self, session: Session, *, user_id: int, show_nsfw: bool, query: str,
        subscription_id: int | None, category: str, nsfw: str,
        domains: list[str] | None, cursor: str | None, page_size: int,
        time_range: str, duration: str, content_type: str, special: str,
    ) -> tuple[list[dict], str | None, dict[str, float]]:
        """read/liked/later 搜索：PG 取 per-user id 集合 → Meili filter id IN [...] 反向交集。

        - PG: 取该用户该 category 的 video_id 集合（最近 5000 个）
        - Meili: 全局索引 filter id IN [集合] + query 文本召回
        - PG: 权限过滤 + OFFSET 分页
        """
        empty_timings = {'recall_ms': 0.0, 'filter_ms': 0.0, 'page_ms': 0.0}
        if not settings.MEILISEARCH_URL:
            logger.warning('user-state search requested but MEILISEARCH_URL not set -- returning empty')
            return [], None, empty_timings

        page = _decode_page_cursor(cursor) if cursor else 1
        offset = max((page - 1) * page_size, 0)

        # 1. PG 取 per-user id 集合
        pg_started = perf_counter()
        user_ids = fetch_user_state_id_set(session, user_id=user_id, category=category)
        pg_ms = self._elapsed_ms(pg_started)
        if not user_ids:
            return [], None, {'recall_ms': pg_ms, 'filter_ms': 0.0, 'page_ms': 0.0}

        # 2. Meili 反向交集召回
        recall_started = perf_counter()
        try:
            recalled_ids = recall_offset_ids(
                query=query, domains=domains, time_range=time_range, duration=duration,
                filter_ids=user_ids, limit=_SEARCH_RECALL_LIMIT,
            )
        except Exception:
            logger.warning('meili recall (reverse-intersection) failed', exc_info=True)
            return [], None, {'recall_ms': pg_ms + self._elapsed_ms(recall_started), 'filter_ms': 0.0, 'page_ms': 0.0}
        recall_ms = pg_ms + self._elapsed_ms(recall_started)

        if not recalled_ids:
            return [], None, {'recall_ms': recall_ms, 'filter_ms': 0.0, 'page_ms': 0.0}

        # 3. PG 权限过滤
        filter_started = perf_counter()
        filtered_ids = filter_recalled_ids(
            session,
            recalled_ids=recalled_ids,
            user_id=user_id, show_nsfw=show_nsfw, subscription_id=subscription_id,
            category='all', nsfw=nsfw, content_type=content_type, special=special,
        )
        filter_ms = self._elapsed_ms(filter_started)

        # 4. OFFSET 分页
        page_ids = filtered_ids[offset:offset + page_size]
        has_more = offset + page_size < len(filtered_ids)
        next_cursor = _encode_page_cursor(page + 1) if has_more else None

        if not page_ids:
            return [], next_cursor, {'recall_ms': recall_ms, 'filter_ms': filter_ms, 'page_ms': 0.0}

        page_started = perf_counter()
        page_items = self._page_loader.load_page(session, user_id=user_id, video_ids=page_ids)
        page_ms = self._elapsed_ms(page_started)
        return page_items.items, next_cursor, {'recall_ms': recall_ms, 'filter_ms': filter_ms, 'page_ms': page_ms}

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
