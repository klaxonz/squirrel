import logging
from collections.abc import Iterable
from threading import Lock
from time import monotonic
from typing import Any

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session

from core.database import get_session
from models.creator import Creator
from models.links import SubscriptionVideo, UserSubscription, VideoCreator
from models.subscription import Subscription
from models.user_video_feed import UserVideoFeed
from models.video import Video
from models.video_history import VideoHistory
from services import user_config_service
from services.nsfw_policy import resolve_effective_nsfw_filter
from services.search_query import parse_search_query
from utils.url_helper import get_site_from_url

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 8
MAX_LIMIT = 20
SUGGESTION_POOL_TTL_SECONDS = 120
SUGGESTION_POOL_MAX_ITEMS = 240
SUGGESTION_RESULT_TTL_SECONDS = 30
CREATOR_FEED_WINDOW = 1200

SOURCE_ORDERS = {
    "home": ("video", "subscription", "creator", "history"),
    "subscribed": ("subscription", "video", "creator", "history"),
    "history": ("history", "video", "subscription", "creator"),
}


def _normalize_query(value: str | None) -> str:
    return " ".join(str(value or "").strip().split())


def _extract_suggestion_term(query: str | None) -> str:
    normalized_query = _normalize_query(query).lower()
    if not normalized_query:
        return ""

    parsed_query = parse_search_query(normalized_query)
    preferred_groups = (
        parsed_query.get("title"),
        parsed_query.get("subscription"),
        parsed_query.get("creator"),
        parsed_query.text_terms,
        parsed_query.get("domain"),
        parsed_query.get("description"),
        parsed_query.get("url"),
    )

    for group in preferred_groups:
        if group:
            return group[-1]

    return normalized_query


def _match_rank(column: Any, query: str) -> Any:
    lowered_column = func.lower(func.coalesce(column, ""))
    return case(
        (lowered_column == query, 0),
        (lowered_column.like(f"{query}%"), 1),
        else_=2,
    )


def _apply_nsfw_visibility(conditions: list[Any], effective_nsfw: str) -> list[Any]:
    if effective_nsfw == "blocked":
        conditions.append(False)
    elif effective_nsfw == "yes":
        conditions.append(UserSubscription.is_nsfw.is_(True))
    elif effective_nsfw == "no":
        conditions.append(UserSubscription.is_nsfw.is_(False))
    return conditions


def _serialize_video_meta(domain: str | None) -> str:
    if domain:
        site_name = get_site_from_url(f"https://{domain}")
        if site_name:
            return f"视频 · {site_name}"
    return "视频"


def _serialize_rows(rows: Iterable[Any], source: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for row in rows:
        value = _normalize_query(getattr(row, "value", None))
        if not value:
            continue

        dedupe_key = value.lower()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        meta = _normalize_query(getattr(row, "meta", None))
        items.append({
            "type": source,
            "value": value,
            "label": value,
            "meta": meta,
        })

    return items


def _dedupe_pool_items(items: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in items:
        value = _normalize_query(item.get("value"))
        item_type = str(item.get("type") or "")
        dedupe_key = (item_type, value.lower())
        if not value or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append({
            "type": item_type,
            "value": value,
            "label": _normalize_query(item.get("label") or value),
            "meta": _normalize_query(item.get("meta") or ""),
        })
        if len(deduped) >= SUGGESTION_POOL_MAX_ITEMS:
            break

    return deduped


def _feed_visibility_predicates(user_id: int, effective_nsfw: str) -> list[Any]:
    predicates: list[Any] = [UserVideoFeed.user_id == user_id]
    if effective_nsfw == "blocked":
        predicates.append(False)
    elif effective_nsfw == "yes":
        predicates.append(UserVideoFeed.is_nsfw.is_(True))
    elif effective_nsfw == "no":
        predicates.append(UserVideoFeed.is_nsfw.is_(False))
    return predicates


def _subscription_visibility_predicates(user_id: int, effective_nsfw: str) -> list[Any]:
    predicates: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
    ]
    _apply_nsfw_visibility(predicates, effective_nsfw)
    return predicates


def _build_video_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    rows = session.execute(
        select(
            Video.title.label("value"),
            UserVideoFeed.domain.label("meta"),
        )
        .select_from(UserVideoFeed)
        .join(Video, Video.id == UserVideoFeed.video_id)
        .where(
            Video.is_deleted.is_(False),
            *_feed_visibility_predicates(user_id, effective_nsfw),
        )
        .order_by(desc(UserVideoFeed.publish_date), desc(UserVideoFeed.video_created_at), desc(Video.id))
        .limit(limit),
    ).all()

    return _dedupe_pool_items(
        {
            "type": "video",
            "value": row.value,
            "label": row.value,
            "meta": _serialize_video_meta(row.meta),
        }
        for row in rows
    )


def _build_subscription_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    rows = session.execute(
        select(
            Subscription.name.label("value"),
            Subscription.type.label("meta"),
        )
        .select_from(UserSubscription)
        .join(Subscription, Subscription.id == UserSubscription.subscription_id)
        .where(*_subscription_visibility_predicates(user_id, effective_nsfw))
        .order_by(desc(Subscription.updated_at), desc(Subscription.id))
        .limit(limit),
    ).all()

    return _dedupe_pool_items(
        {
            "type": "subscription",
            "value": row.value,
            "label": row.value,
            "meta": "频道" if str(row.meta or "").upper() == "CHANNEL" else "订阅",
        }
        for row in rows
    )


def _build_creator_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    recent_feed = (
        select(
            UserVideoFeed.video_id,
            UserVideoFeed.publish_date,
            UserVideoFeed.video_created_at,
        )
        .select_from(UserVideoFeed)
        .where(*_feed_visibility_predicates(user_id, effective_nsfw))
        .order_by(desc(UserVideoFeed.publish_date), desc(UserVideoFeed.video_created_at), desc(UserVideoFeed.video_id))
        .limit(CREATOR_FEED_WINDOW)
        .subquery("recent_feed")
    )

    rows = session.execute(
        select(
            Creator.name.label("value"),
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

    return _dedupe_pool_items(
        {
            "type": "creator",
            "value": row.value,
            "label": row.value,
            "meta": "创作者",
        }
        for row in rows
    )


def _build_history_pool(session: Session, *, user_id: int, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    if effective_nsfw == "blocked":
        return []

    history_query = (
        select(
            Video.title.label("value"),
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
    if effective_nsfw in {"yes", "no"}:
        rows = session.execute(
            history_query.join(UserVideoFeed, and_(
                UserVideoFeed.user_id == user_id,
                UserVideoFeed.video_id == VideoHistory.video_id,
                UserVideoFeed.is_nsfw.is_(effective_nsfw == "yes"),
            )),
        ).all()
    else:
        rows = session.execute(rows).all()

    return _dedupe_pool_items(
        {
            "type": "history",
            "value": row.value,
            "label": row.value,
            "meta": "最近看过",
        }
        for row in rows
    )


def _list_video_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
        Video.is_deleted.is_(False),
        func.lower(Video.title).like(f"%{query}%"),
    ]
    _apply_nsfw_visibility(conditions, effective_nsfw)

    rows = session.execute(
        select(
            Video.title.label("value"),
            Video.domain.label("meta"),
            _match_rank(Video.title, query).label("match_rank"),
            Video.publish_date.label("sort_time"),
            Video.created_at.label("fallback_time"),
        )
        .select_from(Video)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(*conditions)
        .order_by("match_rank", desc(Video.publish_date), desc(Video.created_at), desc(Video.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            "SuggestionRow",
            (),
            {
                "value": row.value,
                "meta": _serialize_video_meta(row.meta),
            },
        )()
        for row in rows
    ]
    return _serialize_rows(normalized_rows, "video")[:limit]


def _list_feed_video_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        UserVideoFeed.user_id == user_id,
        Video.is_deleted.is_(False),
        func.lower(Video.title).like(f"%{query}%"),
    ]

    if effective_nsfw == "blocked":
        return []
    if effective_nsfw == "yes":
        conditions.append(UserVideoFeed.is_nsfw.is_(True))
    elif effective_nsfw == "no":
        conditions.append(UserVideoFeed.is_nsfw.is_(False))

    rows = session.execute(
        select(
            Video.title.label("value"),
            UserVideoFeed.domain.label("meta"),
            _match_rank(Video.title, query).label("match_rank"),
        )
        .select_from(UserVideoFeed)
        .join(Video, Video.id == UserVideoFeed.video_id)
        .where(*conditions)
        .order_by("match_rank", desc(UserVideoFeed.publish_date), desc(UserVideoFeed.video_created_at), desc(Video.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            "SuggestionRow",
            (),
            {
                "value": row.value,
                "meta": _serialize_video_meta(row.meta),
            },
        )()
        for row in rows
    ]
    return _serialize_rows(normalized_rows, "video")[:limit]


def _list_subscription_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
        func.lower(Subscription.name).like(f"%{query}%"),
    ]
    _apply_nsfw_visibility(conditions, effective_nsfw)

    rows = session.execute(
        select(
            Subscription.name.label("value"),
            Subscription.type.label("meta"),
            _match_rank(Subscription.name, query).label("match_rank"),
            Subscription.updated_at.label("sort_time"),
            Subscription.id.label("sort_id"),
        )
        .select_from(UserSubscription)
        .join(Subscription, Subscription.id == UserSubscription.subscription_id)
        .where(*conditions)
        .order_by("match_rank", desc(Subscription.updated_at), desc(Subscription.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            "SuggestionRow",
            (),
            {
                "value": row.value,
                "meta": "频道" if str(row.meta or "").upper() == "CHANNEL" else "订阅",
            },
        )()
        for row in rows
    ]
    return _serialize_rows(normalized_rows, "subscription")[:limit]


def _list_creator_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
        Video.is_deleted.is_(False),
        Creator.is_deleted.is_(False),
        func.lower(Creator.name).like(f"%{query}%"),
    ]
    _apply_nsfw_visibility(conditions, effective_nsfw)

    rows = session.execute(
        select(
            Creator.name.label("value"),
            _match_rank(Creator.name, query).label("match_rank"),
            Video.publish_date.label("sort_time"),
            Creator.id.label("sort_id"),
        )
        .select_from(Creator)
        .join(VideoCreator, VideoCreator.creator_id == Creator.id)
        .join(Video, Video.id == VideoCreator.video_id)
        .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
        .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
        .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
        .where(*conditions)
        .order_by("match_rank", desc(Video.publish_date), desc(Creator.id))
        .limit(limit * 3),
    ).all()

    normalized_rows = [
        type(
            "SuggestionRow",
            (),
            {
                "value": row.value,
                "meta": "创作者",
            },
        )()
        for row in rows
    ]
    return _serialize_rows(normalized_rows, "creator")[:limit]


def _list_history_suggestions(session: Session, *, user_id: int, query: str, effective_nsfw: str, limit: int) -> list[dict[str, str]]:
    conditions: list[Any] = [
        VideoHistory.user_id == user_id,
        Video.is_deleted.is_(False),
        func.lower(Video.title).like(f"%{query}%"),
    ]

    if effective_nsfw == "blocked":
        return []

    if effective_nsfw in {"yes", "no"}:
        nsfw_value = effective_nsfw == "yes"
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
                Video.title.label("value"),
                _match_rank(Video.title, query).label("match_rank"),
                VideoHistory.end_time.label("sort_time"),
                VideoHistory.id.label("sort_id"),
            )
            .select_from(VideoHistory)
            .join(Video, Video.id == VideoHistory.video_id)
            .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
            .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
            .where(*conditions)
            .order_by("match_rank", desc(VideoHistory.end_time), desc(VideoHistory.id))
            .limit(limit * 3),
        ).all()
    else:
        rows = session.execute(
            select(
                Video.title.label("value"),
                _match_rank(Video.title, query).label("match_rank"),
                VideoHistory.end_time.label("sort_time"),
                VideoHistory.id.label("sort_id"),
            )
            .select_from(VideoHistory)
            .join(Video, Video.id == VideoHistory.video_id)
            .where(*conditions)
            .order_by("match_rank", desc(VideoHistory.end_time), desc(VideoHistory.id))
            .limit(limit * 3),
        ).all()

    normalized_rows = [
        type(
            "SuggestionRow",
            (),
            {
                "value": row.value,
                "meta": "最近看过",
            },
        )()
        for row in rows
    ]
    return _serialize_rows(normalized_rows, "history")[:limit]


def _score_candidate(value: str, query: str) -> int:
    lowered_value = value.lower()
    if lowered_value == query:
        return 0
    if lowered_value.startswith(query):
        return 1
    return 2


class SearchSuggestionService:
    def __init__(self, session_factory=get_session, get_user_config=user_config_service.get_config):
        self._session_factory = session_factory
        self._get_user_config = get_user_config
        self._suggestion_pool_cache_lock = Lock()
        self._suggestion_pool_cache: dict[tuple[int, str, str], tuple[float, list[dict[str, str]]]] = {}
        self._suggestion_result_cache: dict[tuple[int, str, str, str, int], tuple[float, list[dict[str, str]]]] = {}

    def _resolve_effective_visibility(self, user_id: int) -> str:
        user_config = self._get_user_config(user_id)
        show_nsfw = user_config.get("showNsfw", False)
        return resolve_effective_nsfw_filter("all", show_nsfw)

    def _build_suggestion_pool(self, user_id: int, scope: str, effective_nsfw: str) -> list[dict[str, str]]:
        with self._session_factory() as session:
            base_limit = 160 if scope == "home" else 120
            pool_parts = {
                "video": _build_video_pool(session, user_id=user_id, effective_nsfw=effective_nsfw, limit=base_limit),
                "subscription": _build_subscription_pool(session, user_id=user_id, effective_nsfw=effective_nsfw, limit=80),
                "creator": _build_creator_pool(session, user_id=user_id, effective_nsfw=effective_nsfw, limit=80),
                "history": _build_history_pool(session, user_id=user_id, effective_nsfw=effective_nsfw, limit=80),
            }

        ordered_items: list[dict[str, str]] = []
        for source in SOURCE_ORDERS.get(scope, SOURCE_ORDERS["home"]):
            ordered_items.extend(pool_parts.get(source, []))

        return _dedupe_pool_items(ordered_items)

    def _get_cached_suggestion_pool(self, user_id: int, scope: str, effective_nsfw: str) -> list[dict[str, str]]:
        cache_key = (int(user_id), str(scope), str(effective_nsfw))
        now = monotonic()
        cached = self._suggestion_pool_cache.get(cache_key)
        if cached and now < cached[0]:
            return cached[1]

        with self._suggestion_pool_cache_lock:
            cached = self._suggestion_pool_cache.get(cache_key)
            if cached and now < cached[0]:
                return cached[1]

            pool = self._build_suggestion_pool(user_id, scope, effective_nsfw)
            self._suggestion_pool_cache[cache_key] = (now + SUGGESTION_POOL_TTL_SECONDS, pool)
            return pool

    def list_search_suggestions(self, user_id: int, query: str | None, scope: str | None = None, limit: int = DEFAULT_LIMIT) -> list[dict[str, str]]:
        normalized_limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        normalized_query = _extract_suggestion_term(query)
        normalized_scope = str(scope or "home").strip().lower() or "home"

        if not normalized_query:
            return []

        effective_nsfw = self._resolve_effective_visibility(user_id)
        result_cache_key = (int(user_id), normalized_scope, effective_nsfw, normalized_query, normalized_limit)
        now = monotonic()
        cached_result = self._suggestion_result_cache.get(result_cache_key)
        if cached_result and now < cached_result[0]:
            return cached_result[1]

        pool = self._get_cached_suggestion_pool(user_id, normalized_scope, effective_nsfw)
        ranked_items: list[tuple[int, int, dict[str, str]]] = []
        for index, item in enumerate(pool):
            value = str(item.get("value") or "")
            if normalized_query not in value.lower():
                continue
            ranked_items.append((_score_candidate(value, normalized_query), index, item))

        ranked_items.sort(key=lambda item: (item[0], item[1]))
        result = [item[2] for item in ranked_items[:normalized_limit]]
        self._suggestion_result_cache[result_cache_key] = (now + SUGGESTION_RESULT_TTL_SECONDS, result)
        return result


_default = SearchSuggestionService()

list_search_suggestions = _default.list_search_suggestions
