import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import and_, case, false, func, literal, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from core.database import get_session
from models.links import SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.subscription_sync_state import SubscriptionSyncState, SyncMode
from models.video_history import VideoHistory
from schemas.subscription.dto.subscription_dto import SubscriptionDto
from services import user_config_service
from services.nsfw_policy import resolve_effective_nsfw_filter
from services.search_query import escape_ilike, normalize_subscription_type_term, parse_search_query
from sql.subscription_sql import get_subscription_sql
from utils.site_catalog import SiteCatalog
from utils.sql_parser import parse_dynamic_sql
from utils.url_helper import extract_top_level_domain, get_site_from_url

logger = logging.getLogger(__name__)


class SubscriptionListService:
    def __init__(self, session_factory=get_session, get_user_config=None):
        self.session_factory = session_factory
        self.get_user_config = get_user_config or user_config_service.get_config

    @staticmethod
    def _contains(column: Any, term: str) -> ColumnElement[bool]:
        return column.ilike(f'%{escape_ilike(term)}%')

    @staticmethod
    def _build_subscription_search_clauses(query: str | None) -> list[Any]:
        parsed_query = parse_search_query(query)
        if not parsed_query.has_terms:
            return []

        clauses: list[Any] = []

        for term in parsed_query.text_terms:
            clauses.append(
                or_(
                    SubscriptionListService._contains(Subscription.name, term),
                    SubscriptionListService._contains(Subscription.description, term),
                    SubscriptionListService._contains(Subscription.url, term),
                ),
            )

        for term in parsed_query.get('subscription'):
            clauses.append(
                or_(
                    SubscriptionListService._contains(Subscription.name, term),
                    SubscriptionListService._contains(Subscription.description, term),
                    SubscriptionListService._contains(Subscription.url, term),
                ),
            )

        for term in parsed_query.get('url'):
            clauses.append(SubscriptionListService._contains(Subscription.url, term))

        for term in parsed_query.get('domain'):
            clauses.append(SubscriptionListService._contains(Subscription.url, term))

        for term in parsed_query.get('description'):
            clauses.append(SubscriptionListService._contains(Subscription.description, term))

        for term in parsed_query.get('title'):
            clauses.append(SubscriptionListService._contains(Subscription.name, term))

        for term in parsed_query.get('type'):
            normalized_type = normalize_subscription_type_term(term)
            if normalized_type:
                clauses.append(Subscription.type == normalized_type)

        return clauses

    @staticmethod
    def _resolved_total_videos_expr(total_videos_column: Any, extracted_count_column: Any) -> Any:
        stored_total = func.coalesce(total_videos_column, 0)
        extracted_total = func.coalesce(extracted_count_column, 0)
        return case(
            (extracted_total > stored_total, extracted_total),
            else_=stored_total,
        )

    @staticmethod
    def _resolve_subscription_nsfw(url: str) -> bool:
        slug, info = SiteCatalog.find_site_by_domain(extract_top_level_domain(url))
        if not info:
            return False
        metadata = info.get('metadata', {})
        return bool(metadata.get('nsfw', False))

    @staticmethod
    def _resolve_site_slug(url: str | None) -> str | None:
        if not url:
            return None
        try:
            slug = get_site_from_url(url)
            if slug:
                return slug

            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            slug, _ = SiteCatalog.find_site_by_domain(domain)
            return slug
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _load_subscription_extract_counts(session: Session, subscription_ids: list[int]) -> dict[int, int]:
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

    @staticmethod
    def _load_subscription_unread_counts(session: Session, user_id: int, subscription_ids: list[int]) -> dict[int, int]:
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
                VideoHistory.video_id is None,
            )
            .group_by(SubscriptionVideo.subscription_id),
        ).all()
        return {
            int(subscription_id): int(unread_count or 0)
            for subscription_id, unread_count in rows
        }

    @staticmethod
    def _load_recent_videos(session: Session, subscription_ids: list[int], limit: int = 10) -> dict[int, list[dict[str, Any]]]:
        if not subscription_ids:
            return {}

        from models.video import Video

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
                'publish_date': SubscriptionListService._serialize_datetime(row.publish_date),
            })

        return grouped

    @staticmethod
    def _serialize_datetime(dt: datetime | None) -> str:
        return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''

    @staticmethod
    def _serialize_subscription_list_item(row: Any, total_extract: int, recent_videos: list[dict[str, Any]] | None = None, unread_count: int = 0) -> dict[str, Any]:
        row_data = row if isinstance(row, dict) else dict(row)
        total_videos = max(int(row_data['total_videos'] or 0), total_extract)
        url = row_data['url']

        return {
            'id': int(row_data['id']),
            'type': row_data['type'],
            'name': row_data['name'],
            'url': url,
            'avatar': row_data['avatar'],
            'description': row_data['description'],
            'total_videos': total_videos,
            'is_deleted': bool(row_data['is_deleted']),
            'extra_data': row_data['extra_data'],
            'created_at': SubscriptionListService._serialize_datetime(row_data['created_at']),
            'updated_at': SubscriptionListService._serialize_datetime(row_data['updated_at']),
            'is_nsfw': bool(row_data['is_nsfw']),
            'is_special_followed': bool(row_data['is_special_followed']),
            'total_extract': total_extract,
            'unread_count': unread_count,
            'sync_status': row_data['sync_status'] or 'idle',
            'last_sync_at': SubscriptionListService._serialize_datetime(row_data['last_sync_at']),
            'last_success_at': SubscriptionListService._serialize_datetime(row_data['last_success_at']),
            'next_sync_at': SubscriptionListService._serialize_datetime(row_data['next_sync_at']),
            'last_error': row_data['last_error'],
            'pending_video_count': int(row_data['pending_video_count'] or 0),
            'site': SubscriptionListService._resolve_site_slug(url),
            'recent_videos': recent_videos or [],
        }

    def list_subscriptions(
            self,
            user_id: int,
            query: str | None,
            type: str | None,
            nsfw: str,
            page: int,
            page_size: int,
            domains: list[str] | None = None,
            special: str = 'all',
    ) -> tuple[list[dict[str, Any]], int]:
        user_config = self.get_user_config(user_id)
        show_nsfw = user_config.get('showNsfw', False)

        with self.session_factory() as session:
            conditions: list[Any] = [
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            ]

            if type:
                conditions.append(Subscription.type == type)

            effective_nsfw = resolve_effective_nsfw_filter(nsfw, show_nsfw)

            if effective_nsfw == 'blocked':
                conditions.append(false())
            elif effective_nsfw == 'yes':
                conditions.append(UserSubscription.is_nsfw.is_(True))
            elif effective_nsfw == 'no':
                conditions.append(UserSubscription.is_nsfw.is_(False))

            if special == 'yes':
                conditions.append(UserSubscription.is_special_followed.is_(True))
            elif special == 'no':
                conditions.append(UserSubscription.is_special_followed.is_(False))

            if domains:
                normalized_domains = [domain for domain in dict.fromkeys(domains) if domain]
                if normalized_domains:
                    conditions.append(
                        or_(*[self._contains(Subscription.url, domain) for domain in normalized_domains]),
                    )

            conditions.extend(self._build_subscription_search_clauses(query))

            count_statement = (
                select(func.count())
                .select_from(UserSubscription)
                .join(Subscription, Subscription.id == UserSubscription.subscription_id)
                .where(*conditions)
            )
            total_count = session.execute(count_statement).scalar() or 0

            statement = (
                select(
                    Subscription.id,
                    Subscription.type,
                    Subscription.name,
                    Subscription.url,
                    Subscription.avatar,
                    Subscription.description,
                    func.coalesce(Subscription.total_videos, 0).label('total_videos'),
                    Subscription.is_deleted,
                    Subscription.extra_data,
                    Subscription.created_at,
                    Subscription.updated_at,
                    UserSubscription.is_nsfw.label('is_nsfw'),
                    UserSubscription.is_special_followed.label('is_special_followed'),
                    literal(0).label('total_extract'),
                    func.coalesce(SubscriptionSyncState.sync_status, 'idle').label('sync_status'),
                    SubscriptionSyncState.last_sync_at.label('last_sync_at'),
                    SubscriptionSyncState.last_success_at.label('last_success_at'),
                    SubscriptionSyncState.next_sync_at.label('next_sync_at'),
                    SubscriptionSyncState.last_error.label('last_error'),
                    func.coalesce(SubscriptionSyncState.pending_video_count, 0).label('pending_video_count'),
                )
                .select_from(UserSubscription)
                .join(Subscription, Subscription.id == UserSubscription.subscription_id)
                .outerjoin(
                    SubscriptionSyncState,
                    and_(
                        SubscriptionSyncState.subscription_id == Subscription.id,
                        SubscriptionSyncState.sync_mode == SyncMode.INCREMENTAL.value,
                    ),
                )
                .where(*conditions)
                .order_by(UserSubscription.is_special_followed.desc(), Subscription.created_at.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )

            results = session.execute(statement).all()
            subscription_ids = [int(row._mapping['id']) for row in results]
            extract_count_map = self._load_subscription_extract_counts(session, subscription_ids)
            unread_count_map = self._load_subscription_unread_counts(session, user_id, subscription_ids)
            recent_videos_map = self._load_recent_videos(session, subscription_ids)

            subscriptions = []
            for row in results:
                row_mapping = row._mapping
                sub_id = int(row_mapping['id'])
                total_extract = extract_count_map.get(sub_id, 0)
                unread_count = unread_count_map.get(sub_id, 0)
                recent_videos = recent_videos_map.get(sub_id, [])
                subscriptions.append(self._serialize_subscription_list_item(row_mapping, total_extract, recent_videos, unread_count))

            return subscriptions, total_count

    def get_subscription_detail(self, subscription_id: int) -> SubscriptionDto:
        from sqlalchemy.sql import text
        with self.session_factory() as session:
            sql = get_subscription_sql()
            params = {
                'subscription_id': subscription_id,
            }
            parse_dynamic_sql(sql, params)
            subscription = session.execute(text(sql), params).first()
            if not subscription:
                return None
            dto = SubscriptionDto.model_validate(subscription._mapping)
            dto.site = self._resolve_site_slug(dto.url)
            return dto

    def list_subscription_options(self, user_id: int) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.execute(
                select(Subscription.id, Subscription.name, Subscription.avatar)
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                    Subscription.is_deleted.is_(False),
                )
                .distinct()
                .order_by(Subscription.name.asc(), Subscription.id.asc()),
            ).all()

        return [
            {
                'subscription_id': subscription_id,
                'subscription_name': subscription_name,
                'subscription_avatar': subscription_avatar,
            }
            for subscription_id, subscription_name, subscription_avatar in rows
        ]


_default = SubscriptionListService()
list_subscriptions = _default.list_subscriptions
get_subscription_detail = _default.get_subscription_detail
list_subscription_options = _default.list_subscription_options
_resolve_subscription_nsfw = _default._resolve_subscription_nsfw
