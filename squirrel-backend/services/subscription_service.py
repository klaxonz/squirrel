import logging
from datetime import datetime
from functools import lru_cache
from typing import Optional, Tuple, List, Dict, Any, Mapping
from urllib.parse import urlparse

from sqlalchemy import select, func, and_, or_, false, case, literal, null
from sqlalchemy.sql import text

from core.database import get_session
from models.links import UserSubscription, SubscriptionVideo
from models.message import Message
from models.subscription import Subscription, ContentType
from models.subscription_sync_state import SubscriptionSyncState, SyncMode
from models.user import User
from models.video_history import VideoHistory
from plugins.manager import get_plugin_manager
from schemas.subscription.dto.subscription_dto import SubscriptionDto
from services.search_query import normalize_subscription_type_term, parse_search_query
from services import user_config_service
from services import subscription_sync_state_service
from services import user_video_feed_service
from services import search_suggestion_service
from services.subscription_runtime_models import (
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
)
from services.nsfw_policy import resolve_effective_nsfw_filter
from sqlfile.subscription_sql import get_subscription_sql
from utils.site_catalog import SiteCatalog
from utils.sql_parser import parse_dynamic_sql
from utils.url_helper import extract_top_level_domain, get_site_from_url

logger = logging.getLogger(__name__)


def _contains(column, term: str):
    return column.ilike(f'%{term}%')


def _build_subscription_search_clauses(query: Optional[str]) -> List[Any]:
    parsed_query = parse_search_query(query)
    if not parsed_query.has_terms:
        return []

    clauses: List[Any] = []

    for term in parsed_query.text_terms:
        clauses.append(
            or_(
                _contains(Subscription.name, term),
                _contains(Subscription.description, term),
                _contains(Subscription.url, term),
            )
        )

    for term in parsed_query.get('subscription'):
        clauses.append(
            or_(
                _contains(Subscription.name, term),
                _contains(Subscription.description, term),
                _contains(Subscription.url, term),
            )
        )

    for term in parsed_query.get('url'):
        clauses.append(_contains(Subscription.url, term))

    for term in parsed_query.get('domain'):
        clauses.append(_contains(Subscription.url, term))

    for term in parsed_query.get('description'):
        clauses.append(_contains(Subscription.description, term))

    for term in parsed_query.get('title'):
        clauses.append(_contains(Subscription.name, term))

    for term in parsed_query.get('type'):
        normalized_type = normalize_subscription_type_term(term)
        if normalized_type:
            clauses.append(Subscription.type == normalized_type)

    return clauses


def _resolved_total_videos_expr(total_videos_column, extracted_count_column):
    stored_total = func.coalesce(total_videos_column, 0)
    extracted_total = func.coalesce(extracted_count_column, 0)
    return case(
        (extracted_total > stored_total, extracted_total),
        else_=stored_total,
    )


@lru_cache(maxsize=256)
def _resolve_site_slug(url: Optional[str]) -> Optional[str]:
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
    except Exception:
        return None


def _load_subscription_extract_counts(session, subscription_ids: List[int]) -> Dict[int, int]:
    if not subscription_ids:
        return {}

    rows = session.execute(
        select(
            SubscriptionVideo.subscription_id,
            func.count(SubscriptionVideo.video_id).label('total_extract'),
        )
        .where(SubscriptionVideo.subscription_id.in_(subscription_ids))
        .group_by(SubscriptionVideo.subscription_id)
    ).all()
    return {
        int(subscription_id): int(total_extract or 0)
        for subscription_id, total_extract in rows
    }


def _load_subscription_unread_counts(session, user_id: int, subscription_ids: List[int]) -> Dict[int, int]:
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
            VideoHistory.video_id == null(),
        )
        .group_by(SubscriptionVideo.subscription_id)
    ).all()
    return {
        int(subscription_id): int(unread_count or 0)
        for subscription_id, unread_count in rows
    }


def _load_recent_videos(session, subscription_ids: List[int], limit: int = 10) -> Dict[int, List[Dict[str, Any]]]:
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
        .order_by(ranked_videos.c.subscription_id.asc(), ranked_videos.c.rank.asc())
    ).all()

    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        sub_id = int(row.subscription_id)
        videos = grouped.setdefault(sub_id, [])
        videos.append({
            'id': int(row.id),
            'title': row.title or '',
            'url': row.url,
            'thumbnail': row.thumbnail,
            'duration': int(row.duration or 0),
            'publish_date': _serialize_datetime(row.publish_date),
        })

    return grouped


def _serialize_datetime(dt: Optional[datetime]) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''


def _serialize_subscription_list_item(row: Mapping[str, Any], total_extract: int, recent_videos: List[Dict[str, Any]] = None, unread_count: int = 0) -> Dict[str, Any]:
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
        'created_at': _serialize_datetime(row_data['created_at']),
        'updated_at': _serialize_datetime(row_data['updated_at']),
        'is_nsfw': bool(row_data['is_nsfw']),
        'is_special_followed': bool(row_data['is_special_followed']),
        'total_extract': total_extract,
        'unread_count': unread_count,
        'sync_status': row_data['sync_status'] or 'idle',
        'last_sync_at': _serialize_datetime(row_data['last_sync_at']),
        'last_success_at': _serialize_datetime(row_data['last_success_at']),
        'next_sync_at': _serialize_datetime(row_data['next_sync_at']),
        'last_error': row_data['last_error'],
        'pending_video_count': int(row_data['pending_video_count'] or 0),
        'site': _resolve_site_slug(url),
        'recent_videos': recent_videos or [],
    }



def _detect_subscription_type(url: str) -> str:
    """检测订阅类型：播放列表或频道"""
    # YouTube 播放列表检测
    if 'youtube.com' in url or 'youtu.be' in url:
        if 'list=' in url or '/playlist?' in url:
            return ContentType.PLAYLIST
    
    # Bilibili 播放列表检测（收藏夹、合集）
    if 'bilibili.com' in url:
        if '/favlist' in url or 'fid=' in url:
            return ContentType.PLAYLIST
        if '/season/' in url or 'season_id=' in url:
            return ContentType.PLAYLIST
    
    # 默认为频道
    return ContentType.CHANNEL


def get_subscription_by_id(subscription_id: int):
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        return subscription


def get_subscription_by_url_and_name(url: str, name: str):
    with get_session() as session:
        subscription = session.scalars(select(Subscription).where(
            Subscription.url == url,
            Subscription.name == name
        )).first()
        return subscription


def get_active_user_subscription_by_url(user_id: int, url: str):
    with get_session() as session:
        subscription = session.execute(
            select(Subscription)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.url == url,
                Subscription.is_deleted == False,
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted == False,
            )
        ).scalar_one_or_none()
        return subscription


def get_active_user_subscription_url_map(user_id: int) -> Dict[str, int]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription.url, Subscription.id)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.is_deleted.is_(False),
                Subscription.url.is_not(None),
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
            )
        ).all()
        return {url: subscription_id for url, subscription_id in rows if url}


def get_deleted_user_subscription_urls(user_id: int) -> set[str]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription.url)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                Subscription.url.is_not(None),
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(True),
            )
        ).all()
        return {url for url, in rows if url}


def create_subscription(user_id: int, subscribe_info: SubscriptionMeta):  
    with get_session() as session:
        user_subscription = None
        subscription = get_subscription_by_url_and_name(url=subscribe_info.url, name=subscribe_info.name)
        if subscription:
            subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)
            return subscription
        else:
            # 检测订阅类型：播放列表还是频道
            content_type = _detect_subscription_type(subscribe_info.url)
            
            subscription = Subscription(
                type=content_type,
                name=subscribe_info.name,
                url=subscribe_info.url,
                avatar=subscribe_info.avatar,
                description=None,
                extra_data={}
            )
            session.add(subscription)
            session.flush()
        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription.id
            )).first()
        if not user_subscription:
            is_nsfw = False
            url = subscribe_info.url
            if 'pornhub.com' in url or 'javdb.com' in url:
                is_nsfw = True

            user_subscription = UserSubscription(
                user_id=user_id,
                subscription_id=subscription.id,
                is_nsfw=is_nsfw
            )
            session.add(user_subscription)
        session.commit()
    if user_subscription is not None:
        user_video_feed_service.backfill_user_subscription_feed(user_id, subscription.id, user_subscription.is_nsfw)
    subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)
    return subscription


def list_subscriptions(
        user_id: int,
        query: Optional[str],
        type: Optional[str],
        nsfw: str,
        page: int,
        page_size: int,
        domains: Optional[List[str]] = None,
        special: str = 'all',
) -> Tuple[List[Dict[str, Any]], int]:
    """Get subscription list"""

    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    with get_session() as session:
        conditions: List[Any] = [
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
                    or_(*[_contains(Subscription.url, domain) for domain in normalized_domains])
                )

        conditions.extend(_build_subscription_search_clauses(query))

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
        extract_count_map = _load_subscription_extract_counts(session, subscription_ids)
        unread_count_map = _load_subscription_unread_counts(session, user_id, subscription_ids)
        recent_videos_map = _load_recent_videos(session, subscription_ids)

        subscriptions = []
        for row in results:
            row_mapping = row._mapping
            sub_id = int(row_mapping['id'])
            total_extract = extract_count_map.get(sub_id, 0)
            unread_count = unread_count_map.get(sub_id, 0)
            recent_videos = recent_videos_map.get(sub_id, [])
            subscriptions.append(_serialize_subscription_list_item(row_mapping, total_extract, recent_videos, unread_count))

        return subscriptions, total_count


def get_subscription_detail(subscription_id: int) -> SubscriptionDto:
    with get_session() as session:
        sql = get_subscription_sql()
        params = {
            'subscription_id': subscription_id
        }
        parse_dynamic_sql(sql, params)
        subscription = session.execute(text(sql), params).first()
        if not subscription:
            return None
        dto = SubscriptionDto.model_validate(subscription._mapping)
        dto.site = _resolve_site_slug(dto.url)
        return dto


def list_subscription_options(user_id: int) -> List[Dict[str, Any]]:
    with get_session() as session:
        rows = session.execute(
            select(Subscription.id, Subscription.name, Subscription.avatar)
            .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            )
            .distinct()
            .order_by(Subscription.name.asc(), Subscription.id.asc())
        ).all()

    return [
        {
            'subscription_id': subscription_id,
            'subscription_name': subscription_name,
            'subscription_avatar': subscription_avatar,
        }
        for subscription_id, subscription_name, subscription_avatar in rows
    ]


def update_subscription(
        subscription_id: int,
        update_data: Dict[str, Any]
) -> bool:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return False

        for key, value in update_data.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        session.add(subscription)
        session.commit()
        updated = True
    try:
        search_suggestion_service.rebuild_users_for_subscription(subscription_id)
    except Exception as exc:
        logger.warning('Search suggestion subscription refresh skipped: %s', exc)
    return updated


def toggle_status(subscription_id: int, status: bool, field: str) -> bool:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return False
        try:
            setattr(subscription, field, status)
            session.add(subscription)
            session.commit()
            return True
        except ValueError:
            return False


def toggle_nsfw_status(user_id: int, subscription_id: int, is_nsfw: bool) -> bool:
    with get_session() as session:
        user_sub = session.execute(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).scalar_one_or_none()
        if not user_sub:
            return False
        
        user_sub.is_nsfw = is_nsfw
        session.commit()
    user_video_feed_service.update_user_subscription_nsfw(user_id, subscription_id, is_nsfw)
    return True


def toggle_special_follow_status(user_id: int, subscription_id: int, is_special_followed: bool) -> bool:
    with get_session() as session:
        user_sub = session.execute(
            select(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).scalar_one_or_none()
        if not user_sub:
            return False

        user_sub.is_special_followed = is_special_followed
        session.commit()
    return True


def handle_subscribe_request(url: str, user_id: int) -> Subscription:
    """
    处理订阅请求（用于消息队列消费者）
    
    Args:
        url: 订阅URL
        user_id: 用户ID
        
    Returns:
        订阅对象
    """
    existing_subscription = get_active_user_subscription_by_url(user_id=user_id, url=url)
    if existing_subscription:
        return existing_subscription

    subscribe_info = _load_runtime_subscription_meta(url)

    subscription = get_subscription_by_url_and_name(url, subscribe_info.name)

    if subscription:
        restore_subscription(subscription.id, user_id)
        return get_subscription_by_id(subscription.id)

    subscription = create_subscription(user_id, subscribe_info)
    return subscription


def restore_subscription(subscription_id: int, user_id: int) -> None:
    """
    恢复已删除的订阅
    
    Args:
        subscription_id: 订阅ID
        user_id: 用户ID
    """
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription:
            return
        
        subscription.is_deleted = False
        
        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.user_id == user_id
            )
        ).first()
        
        if user_subscription and user_subscription.is_deleted:
            user_subscription.is_deleted = False
        elif not user_subscription:
            user_subscription = UserSubscription(
                subscription_id=subscription_id,
                user_id=user_id,
                is_deleted=False,
                is_nsfw=False,
            )
            session.add(user_subscription)
        
        session.commit()
    user_video_feed_service.backfill_user_subscription_feed(user_id, subscription_id, user_subscription.is_nsfw)
    subscription = get_subscription_by_id(subscription_id)
    if subscription:
        subscription_sync_state_service.ensure_sync_states(subscription.id, subscription.url)


def create_subscribe_message(url: str, user_id: int) -> Dict[str, Any]:
    import json
    from common import constants
    from queues.producer import RedisStreamProducer

    with get_session() as session:
        task = {
            "url": url,
            "user_id": user_id
        }
        message = Message(body=json.dumps(task))
        session.add(message)
        session.commit()
        dump_json = message.to_dict()
        RedisStreamProducer().send(constants.QUEUE_SUBSCRIBE, dump_json)
    return dump_json


def unsubscribe_by_id(user_id: int, subscription_id: int) -> bool:
    with get_session() as session:
        if not subscription_id:
            return False

        subscription = session.scalars(
            select(Subscription).where(Subscription.id == subscription_id)
        ).first()

        if not subscription:
            return False

        active_user_subscriptions = session.scalars(
            select(UserSubscription).where(
                UserSubscription.subscription_id == subscription.id,
                UserSubscription.is_deleted.is_(False),
            )
        ).all()

        for user_subscription in active_user_subscriptions:
            user_subscription.is_deleted = True

        subscription.is_deleted = True
        session.commit()

    user_video_feed_service.remove_subscription_feed(subscription_id)
    subscription_sync_state_service.deactivate_sync_states(
        subscription_id,
        reason='manual_unsubscribe',
    )

    return True


def check_subscription_status(user_id: int, url: str) -> Dict[str, Any]:
    if not url:
        return {
            'is_subscribed': False,
            'subscription_id': None,
        }
    with get_session() as session:
        subscription = session.scalars(
            select(Subscription).where(
                Subscription.url == url,
                Subscription.is_deleted.is_(False),
            )
        ).first()
        return {
            'is_subscribed': subscription is not None,
            'subscription_id': subscription.id if subscription else None,
        }


def get_user_subscription_nsfw(user_id: int, subscription_id: int) -> Optional[bool]:
    with get_session() as session:
        user_sub = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if user_sub:
            return user_sub.is_nsfw
        return None


def get_user_subscription_special_followed(user_id: int, subscription_id: int) -> Optional[bool]:
    with get_session() as session:
        user_sub = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if user_sub:
            return user_sub.is_special_followed
        return None


def verify_subscription_access(user_id: int, subscription_id: int) -> Tuple[Optional[Subscription], str]:
    with get_session() as session:
        subscription = session.get(Subscription, subscription_id)
        if not subscription or subscription.is_deleted:
            return None, "not_found"

        user_subscription = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id == subscription_id,
                UserSubscription.is_deleted.is_(False)
            )
        ).first()
        if not user_subscription:
            return None, "forbidden"

        session.expunge(subscription)
        return subscription, "ok"


def _dedupe_import_items(subscriptions: List[SubscriptionImportItem]) -> List[SubscriptionImportItem]:
    seen_urls = set()
    result = []
    for sub in subscriptions:
        if not sub.url or sub.url in seen_urls:
            continue
        seen_urls.add(sub.url)
        result.append(sub)
    return result


def _load_runtime_import_batch(
    site_name: str,
    *,
    cursor_payload: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> SubscriptionImportBatchResult:
    payload: Dict[str, Any] = {}
    if cursor_payload:
        payload['cursor_payload'] = dict(cursor_payload)
    if limit is not None:
        payload['limit'] = limit

    response = get_plugin_manager().gateway.invoke(
        'import_subscriptions',
        payload=payload or None,
        site_name=site_name,
    )
    if not response.ok:
        message = response.error.message if response.error else f'Plugin import failed for site: {site_name}'
        raise ValueError(message)

    payload = response.data
    if not isinstance(payload, dict):
        raise ValueError(f'Plugin import payload must be an object for site: {site_name}')

    batch = SubscriptionImportBatchResult.from_dict(payload)
    batch.items = _dedupe_import_items(batch.items)
    return batch


def _load_runtime_import_items(site_name: str) -> List[SubscriptionImportItem]:
    items: List[SubscriptionImportItem] = []
    cursor_payload: Optional[Dict[str, Any]] = None

    while True:
        batch = _load_runtime_import_batch(
            site_name,
            cursor_payload=cursor_payload,
        )
        items.extend(batch.items)
        if not batch.has_more:
            break
        cursor_payload = batch.cursor_payload

    return _dedupe_import_items(items)


def get_runtime_supported_sites(capability: str) -> List[str]:
    snapshot = get_plugin_manager().get_snapshot()
    return sorted({
        registration.site_name
        for registration in snapshot.registrations
        if registration.capability == capability and registration.site_name
    })


def list_user_ids() -> List[int]:
    with get_session() as session:
        rows = session.execute(select(User.id).order_by(User.id.asc())).all()
        return [user_id for user_id, in rows]


def get_enabled_runtime_import_sites() -> List[str]:
    return [
        site
        for site in get_runtime_supported_sites('import_subscriptions')
        if SiteCatalog.is_site_enabled(site=site)
    ]


def _load_runtime_subscription_meta(url: str) -> SubscriptionMeta:
    domain = extract_top_level_domain(url)
    parsed_url = urlparse(url)
    payload = {
        'url': url,
        'domain': domain or parsed_url.netloc.lower().split(':')[0],
    }
    response = get_plugin_manager().gateway.invoke(
        'resolve_subscription',
        payload=payload,
        domain=domain or None,
    )
    if not response.ok:
        message = response.error.message if response.error else f'Plugin subscription resolution failed for url: {url}'
        raise ValueError(message)

    if not isinstance(response.data, dict):
        raise ValueError(f'Plugin resolve_subscription payload must be an object for url: {url}')

    return SubscriptionMeta.from_dict(response.data)


def preview_user_subscriptions(
    site_name: str,
    user_id: int,
    *,
    cursor_payload: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    预览用户在指定站点的订阅列表（不实际导入）
    
    Args:
        site_name: 站点名称（如 'bilibili', 'youtube' 等）
        user_id: 用户ID

    Returns:
        预览结果：{
            'site': 站点名称,
            'total': 找到的订阅数量,
            'subscriptions': 订阅列表 [{'url': '...', 'name': '...', 'avatar': '...'}, ...]
        }
    """
    try:
        import_batch = _load_runtime_import_batch(
            site_name,
            cursor_payload=cursor_payload,
            limit=limit,
        )
        subscriptions = import_batch.items

        logger.info(f"Found {len(subscriptions)} subscriptions from {site_name} for preview")

        imported_url_map = get_active_user_subscription_url_map(user_id)
        imported_count = 0

        preview_subscriptions = []
        for sub in subscriptions:
            data = sub.to_dict()
            is_imported = sub.url in imported_url_map
            data["is_imported"] = is_imported
            if is_imported:
                data["subscription_id"] = imported_url_map[sub.url]
                imported_count += 1
            preview_subscriptions.append(data)

        return {
            'site': site_name,
            'total': import_batch.total_available if import_batch.total_available is not None else len(subscriptions),
            'loaded': len(subscriptions),
            'imported': imported_count,
            'not_imported': len(subscriptions) - imported_count,
            'subscriptions': preview_subscriptions,
            'has_more': import_batch.has_more,
            'cursor_payload': import_batch.cursor_payload,
            'stop_reason': import_batch.stop_reason,
        }

    except Exception as e:
        logger.error(f"Failed to preview subscriptions from {site_name}: {e}", exc_info=True)
        raise


def _enqueue_subscriptions_async(subscriptions: List[SubscriptionImportItem], user_id: int, site_name: str):
    """
    在后台线程中投递订阅任务到消息队列
    
    Args:
        subscriptions: 订阅列表
        user_id: 用户ID
        site_name: 站点名称
    """
    import logging
    import json
    from common import constants
    from queues.producer import RedisStreamProducer
    
    logger = logging.getLogger()
    
    try:
        enqueued = 0
        producer = RedisStreamProducer()

        with get_session() as session:
            for sub in subscriptions:
                url = sub.url
                try:
                    # 创建订阅任务
                    task = {
                        "url": url,
                        "name": sub.name,
                        "avatar": sub.avatar,
                        "user_id": user_id
                    }
                    message = Message(body=json.dumps(task))
                    session.add(message)
                    session.flush()  # 获取 message.id
                    
                    # 投递到队列
                    dump_json = message.to_dict()
                    producer.send(constants.QUEUE_SUBSCRIBE, dump_json)
                    enqueued += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to enqueue subscription {url}: {e}")
            
            session.commit()

        logger.info(f"Enqueued {enqueued}/{len(subscriptions)} subscription tasks from {site_name}")
        
    except Exception as e:
        logger.error(f"Failed to enqueue subscriptions from {site_name}: {e}", exc_info=True)


def import_user_subscriptions(
    site_name: str,
    user_id: int,
    selected_urls: Optional[List[str]] = None,
    *,
    use_background_thread: bool = True,
    respect_manual_unsubscribe: bool = False,
) -> Dict[str, Any]:
    """
    从指定站点导入用户的所有订阅（异步）
    
    Args:
        site_name: 站点名称（如 'bilibili', 'youtube' 等）
        user_id: 用户ID
        
    Returns:
        导入结果：{
            'total': 总数
        }
    """
    import threading

    try:
        if selected_urls is not None:
            subscriptions = _dedupe_import_items([
                SubscriptionImportItem(url=url)
                for url in selected_urls
                if url
            ])
            found_total = None
        else:
            subscriptions = _load_runtime_import_items(site_name)
            found_total = len(subscriptions)
            logger.info(f"Found {found_total} subscriptions from {site_name}")
        selected_total = len(subscriptions)

        imported_url_map = get_active_user_subscription_url_map(user_id)
        imported_urls = set(imported_url_map.keys())
        manually_unsubscribed_urls = (
            get_deleted_user_subscription_urls(user_id)
            if respect_manual_unsubscribe
            else set()
        )
        to_import = [
            s for s in subscriptions
            if s.url not in imported_urls and s.url not in manually_unsubscribed_urls
        ]

        if to_import:
            if use_background_thread:
                thread = threading.Thread(
                    target=_enqueue_subscriptions_async,
                    args=(to_import, user_id, site_name),
                    daemon=True
                )
                thread.start()
                logger.info(f"Started background thread to enqueue {len(to_import)} subscriptions")
            else:
                _enqueue_subscriptions_async(to_import, user_id, site_name)
                logger.info(f"Synchronously enqueued {len(to_import)} subscriptions")
        else:
            logger.info("No new subscriptions to import")

        # 立即返回
        return {
            'total': len(to_import),
            'found': found_total,
            'selected': selected_total,
            'skipped': selected_total - len(to_import)
        }
        
    except Exception as e:
        logger.error(f"Failed to import subscriptions from {site_name}: {e}", exc_info=True)
        raise


def auto_import_missing_subscriptions(
    *,
    user_ids: Optional[List[int]] = None,
    site_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    resolved_user_ids = list(dict.fromkeys(user_ids or list_user_ids()))
    resolved_site_names = list(dict.fromkeys(site_names or get_enabled_runtime_import_sites()))

    summary = {
        'users': len(resolved_user_ids),
        'sites': len(resolved_site_names),
        'imported': 0,
        'skipped': 0,
        'failed': 0,
    }

    if not resolved_user_ids or not resolved_site_names:
        logger.info(
            "Skipped automatic subscription import: users=%s, sites=%s",
            len(resolved_user_ids),
            len(resolved_site_names),
        )
        return summary

    for user_id in resolved_user_ids:
        for site_name in resolved_site_names:
            try:
                result = import_user_subscriptions(
                    site_name,
                    user_id,
                    use_background_thread=False,
                    respect_manual_unsubscribe=True,
                )
                summary['imported'] += int(result.get('total') or 0)
                summary['skipped'] += int(result.get('skipped') or 0)
            except Exception as exc:
                summary['failed'] += 1
                logger.error(
                    "Automatic subscription import failed for user_id=%s site=%s: %s",
                    user_id,
                    site_name,
                    exc,
                    exc_info=True,
                )

    logger.info(
        "Automatic subscription import completed: users=%s, sites=%s, imported=%s, skipped=%s, failed=%s",
        summary['users'],
        summary['sites'],
        summary['imported'],
        summary['skipped'],
        summary['failed'],
    )
    return summary
