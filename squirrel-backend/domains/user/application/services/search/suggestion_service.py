from threading import Lock
from time import monotonic

from sqlalchemy import select

import domains.user.application.services.config as user_config_service
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.user.application.services.search.suggestions.formatting import dedupe_pool_items
from domains.user.application.services.search.suggestions.pools import (
    SOURCE_ORDERS,
    build_creator_pool,
    build_history_pool,
    build_subscription_pool,
    build_video_pool,
)
from domains.user.application.services.search.suggestions.text import extract_suggestion_term, score_candidate
from domains.video.application.services.moderation.nsfw_policy import resolve_effective_nsfw_filter
from infrastructure.database.session import get_session

DEFAULT_LIMIT = 8
MAX_LIMIT = 20
SUGGESTION_POOL_TTL_SECONDS = 120
SUGGESTION_RESULT_TTL_SECONDS = 30


class SearchSuggestionService:
    def __init__(self, session_factory=get_session, get_user_config=user_config_service.get_config):
        self._session_factory = session_factory
        self._get_user_config = get_user_config
        self._suggestion_pool_cache_lock = Lock()
        self._suggestion_pool_cache: dict[tuple[int, str, str], tuple[float, list[dict[str, str]]]] = {}
        self._suggestion_result_cache: dict[tuple[int, str, str, str, int], tuple[float, list[dict[str, str]]]] = {}

    def _resolve_effective_visibility(self, user_id: int) -> str:
        user_config = self._get_user_config(user_id)
        show_nsfw = user_config.get('showNsfw', False)
        return resolve_effective_nsfw_filter('all', show_nsfw)

    def _build_suggestion_pool(self, user_id: int, scope: str, effective_nsfw: str) -> list[dict[str, str]]:
        with self._session_factory() as session:
            base_limit = 160 if scope == 'home' else 120
            pool_parts = {
                'video': build_video_pool(session, user_id=user_id, effective_nsfw=effective_nsfw, limit=base_limit),
                'subscription': build_subscription_pool(
                    session, user_id=user_id, effective_nsfw=effective_nsfw, limit=80
                ),
                'creator': build_creator_pool(session, user_id=user_id, effective_nsfw=effective_nsfw, limit=80),
                'history': build_history_pool(session, user_id=user_id, effective_nsfw=effective_nsfw, limit=80),
            }

        ordered_items: list[dict[str, str]] = []
        for source in SOURCE_ORDERS.get(scope, SOURCE_ORDERS['home']):
            ordered_items.extend(pool_parts.get(source, []))

        return dedupe_pool_items(ordered_items)

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

    def invalidate_user(self, user_id: int) -> None:
        normalized_user_id = int(user_id)
        with self._suggestion_pool_cache_lock:
            self._suggestion_pool_cache = {
                key: value for key, value in self._suggestion_pool_cache.items() if key[0] != normalized_user_id
            }
            self._suggestion_result_cache = {
                key: value for key, value in self._suggestion_result_cache.items() if key[0] != normalized_user_id
            }

    def invalidate_users_for_subscription(self, subscription_id: int) -> None:
        with self._session_factory() as session:
            user_ids = (
                session.execute(
                    select(UserSubscription.user_id).where(
                        UserSubscription.subscription_id == subscription_id,
                        UserSubscription.is_deleted.is_(False),
                    ),
                )
                .scalars()
                .all()
            )

        for user_id in user_ids:
            self.invalidate_user(int(user_id))

    def list_search_suggestions(
        self,
        user_id: int,
        query: str | None,
        scope: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict[str, str]]:
        normalized_limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        normalized_query = extract_suggestion_term(query)
        normalized_scope = str(scope or 'home').strip().lower() or 'home'

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
            value = str(item.get('value') or '')
            if normalized_query not in value.lower():
                continue
            ranked_items.append((score_candidate(value, normalized_query), index, item))

        ranked_items.sort(key=lambda item: (item[0], item[1]))
        result = [item[2] for item in ranked_items[:normalized_limit]]
        self._suggestion_result_cache[result_cache_key] = (now + SUGGESTION_RESULT_TTL_SECONDS, result)
        return result


search_suggestion_service = SearchSuggestionService()

list_search_suggestions = search_suggestion_service.list_search_suggestions
invalidate_user = search_suggestion_service.invalidate_user
invalidate_users_for_subscription = search_suggestion_service.invalidate_users_for_subscription
