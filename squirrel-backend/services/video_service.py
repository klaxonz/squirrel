import json
import logging
from datetime import datetime, timedelta
import hashlib
from time import perf_counter
from typing import Any, List, Tuple, Optional, Dict
from urllib.parse import parse_qs, urlencode, urlparse
from crawl.runtime_errors import RuntimeErrorCode
from sqlalchemy import select, func, and_, case, exists, false, literal
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload, with_loader_criteria
from core.database import get_session
from services.video_query import (
    build_base_video_query,
    category_predicate,
    duration_predicate,
)
from services.search_query import normalize_subscription_type_term, parse_search_query


from core.exceptions.video_exceptions import UnsupportedDomainError, VideoUrlExtractionError
from models.creator import Creator
from models.links import SubscriptionVideo, UserSubscription, VideoCreator
from models.subscription import Subscription
from models.user_video_feed import UserVideoFeed
from models.video import Video
from models.video_clip_marker import VideoClipMarker
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from plugins.manager import get_plugin_manager
from schemas.video.dto.video_dto import QualityOptionDto, VideoUrlDto

from services import user_config_service
from services.video_clip_marker_service import serialize_marker
from services.nsfw_policy import resolve_effective_nsfw_filter
from utils import url_helper
from utils.url_helper import extract_top_level_domain
from utils.site_catalog import SiteCatalog
from core.cache import redis_client
from core.cookie_config import get_site_cookies_file_path
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service

logger = logging.getLogger()

VIDEO_URL_CACHE_TTL = 300


def _elapsed_ms(start_time: float) -> float:
    return round((perf_counter() - start_time) * 1000, 3)


def _unwrap_proxy_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return url

    parsed = urlparse(url)
    if parsed.path != '/api/video/proxy':
        return url

    query = parse_qs(parsed.query)
    upstream_urls = query.get('url') or []
    return upstream_urls[0] if upstream_urls else url


def _append_direct_flag(url: Optional[str]) -> Optional[str]:
    if not url:
        return url

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query['direct'] = ['1']
    return parsed._replace(query=urlencode(query, doseq=True)).geturl()


def _playback_cache_scope(client_type: Optional[str], *, prefer_direct_urls: bool) -> str:
    normalized_client_type = str(client_type or '').strip().lower()
    if not normalized_client_type:
        return 'default'
    mode = 'direct' if prefer_direct_urls else 'proxied'
    return f'{normalized_client_type}:{mode}'


def _file_cache_scope(path) -> str:
    try:
        payload = path.read_bytes()
    except OSError:
        return 'none'
    return hashlib.sha256(payload).hexdigest()[:16]


def _auth_cache_scope(site_slug: Optional[str]) -> str:
    if site_slug != 'youtube':
        return 'auth:default'

    from services.youtube_oauth_service import get_oauth_cache_scope

    oauth_scope = get_oauth_cache_scope()
    cookie_scope = _file_cache_scope(get_site_cookies_file_path('youtube'))
    return f'{oauth_scope}:cookie:{cookie_scope}'


def _finalize_video_url_dto(dto: VideoUrlDto, *, prefer_direct_urls: bool) -> VideoUrlDto:
    finalized = dto.model_copy(deep=True)
    if not prefer_direct_urls:
        return finalized

    finalized.video_url = _unwrap_proxy_url(finalized.video_url)
    finalized.audio_url = _unwrap_proxy_url(finalized.audio_url)
    finalized.mpd_url = _append_direct_flag(finalized.mpd_url)
    return finalized


def _looks_like_hls_url(url: Optional[str]) -> bool:
    if not url:
        return False
    lowered = str(url).lower()
    return '.m3u8' in lowered or 'format=m3u8' in lowered


def _normalize_quality_options(qualities: Optional[List[QualityOptionDto]]) -> list[QualityOptionDto]:
    if not qualities:
        return []

    normalized: list[QualityOptionDto] = []
    for index, item in enumerate(qualities):
        item_id = str(item.id or item.value or item.label or index)
        item_value = item.value or item_id
        normalized.append(item.model_copy(update={
            'id': item_id,
            'value': item_value,
            'label': item.label or item_value,
        }))

    normalized.sort(key=lambda item: ((item.height or 0), (item.bandwidth or 0)), reverse=True)
    return normalized


def _infer_stream_type(dto: VideoUrlDto) -> str:
    if dto.stream_type:
        return dto.stream_type
    if dto.mpd_url or (dto.video_url and dto.audio_url):
        return 'dash'
    if _looks_like_hls_url(dto.video_url) or _looks_like_hls_url(dto.audio_url):
        return 'hls'
    return 'progressive'


def _normalize_playback_contract(dto: VideoUrlDto, *, video_id: int) -> VideoUrlDto:
    normalized = dto.model_copy(deep=True)
    if normalized.video_url and normalized.audio_url and not normalized.mpd_url:
        normalized.mpd_url = f'/api/video/mpd?video_id={video_id}'

    stream_type = _infer_stream_type(normalized)
    qualities = _normalize_quality_options(normalized.qualities)
    available_quality_ids = {str(item.id) for item in qualities if item.id}

    default_quality_id = str(normalized.default_quality_id) if normalized.default_quality_id else None
    if default_quality_id not in available_quality_ids:
        default_quality_id = str(qualities[0].id) if qualities else None

    supports_manual_quality = normalized.supports_manual_quality or len(qualities) > 1

    return normalized.model_copy(update={
        'stream_type': stream_type,
        'qualities': qualities or None,
        'default_quality_id': default_quality_id,
        'supports_manual_quality': supports_manual_quality,
    })


def get_video_by_url(url: str) -> Video:
    with get_session() as session:
        video = session.scalars(select(Video).where(Video.url == url)).first()
        return video


def get_videos_by_urls(urls: List[str]) -> Dict[str, Video]:
    if not urls:
        return {}
    with get_session() as session:
        rows = session.scalars(
            select(Video).where(Video.url.in_(urls))
        ).all()
        return {video.url: video for video in rows}


def get_video_by_id(video_id: int) -> Video:
    with get_session() as session:
        video = session.get(Video, video_id)
        return video


def create_video(url: str, title: str, publish_date: datetime, thumbnail: str, duration: int) -> Video:
    with get_session() as session:
        video = Video()
        video.url = url
        video.domain = url_helper.normalize_domain(url)
        video.title = title
        video.publish_date = publish_date
        video.thumbnail = thumbnail
        video.duration = duration
        session.add(video)
        session.commit()
        return video


def _parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    try:
        return datetime.fromisoformat(normalized.replace('Z', '+00:00'))
    except ValueError:
        return None


def _video_extra_profiles(video: Video, key: str) -> list[dict]:
    extra_data = video.extra_data if isinstance(video.extra_data, dict) else {}
    profiles = extra_data.get(key)
    if not isinstance(profiles, list):
        return []

    normalized = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        name = str(profile.get('name') or '').strip()
        url = str(profile.get('url') or '').strip()
        if not name and not url:
            continue
        item = {
            'id': profile.get('id'),
            'name': name,
            'url': url,
            'type': profile.get('type'),
            'avatar': profile.get('avatar'),
            'is_nsfw': profile.get('is_nsfw'),
        }
        if profile.get('description') is not None:
            item['description'] = profile.get('description')
        if profile.get('site') is not None:
            item['site'] = profile.get('site')
        normalized.append(item)

    return normalized


def _merge_profiles(primary: list[dict], extra: list[dict]) -> list[dict]:
    merged = []
    seen = set()
    for profile in [*primary, *extra]:
        key = (
            str(profile.get('id') or '').strip(),
            str(profile.get('url') or '').strip(),
            str(profile.get('name') or '').strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(profile)
    return merged


def save_remote_video(data: dict) -> Video:
    url = str(data.get('url') or '').strip()
    title = str(data.get('title') or '').strip()
    if not url:
        raise ValueError('url is required')
    if not title:
        raise ValueError('title is required')

    with get_session() as session:
        video = session.scalars(select(Video).where(Video.url == url)).first()
        if video:
            return video

        publish_date = _parse_optional_datetime(data.get('publish_date') or data.get('uploaded_at'))
        extra_data = {
            'source': 'remote',
            'site': data.get('site') or None,
            'subscriptions': data.get('subscriptions') or [],
            'actors': data.get('actors') or [],
        }

        video = Video(
            url=url,
            domain=url_helper.normalize_domain(url),
            title=title,
            publish_date=publish_date,
            thumbnail=data.get('thumbnail') or None,
            duration=data.get('duration'),
            description=data.get('description') or None,
            extra_data=extra_data,
        )
        session.add(video)
        session.commit()
        session.refresh(video)
        return video



def get_random_video(
        user_id: int,
        category: Optional[str] = None,
        subscription_id: Optional[int] = None,
        nsfw: str = 'all',
        domains: Optional[List[str]] = None,
        query: Optional[str] = None,
        time_range: str = 'all',
        duration: str = 'all',
        content_type: str = 'all',
) -> Optional[Video]:
    """返回符合过滤条件的一个随机视频（已发布）。

    - 遵循用户 NSFW 偏好（通过 user_config）
    - 支持分类：all/read/unread/preview/liked/later（与列表页一致）
    - 支持 subscription/site(query by domains)/keyword 过滤
    """
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    # 基础可重用查询
    base = build_base_video_query(
        user_id, show_nsfw, subscription_id, query, nsfw, domains,
        time_range, duration, content_type,
    )
    base = base.where(category_predicate(user_id, category))


    with get_session() as session:
        bind = session.get_bind()
        dialect_name = getattr(getattr(bind, 'dialect', None), 'name', '') or ''

        # Choose DB-specific random function
        if dialect_name in ('postgresql', 'sqlite'):
            order_random = func.random()
        elif dialect_name in ('mysql', 'mariadb'):
            order_random = func.rand()
        else:
            order_random = func.random()

        random_row = session.execute(
            base.order_by(order_random).limit(1)
        ).first()
        return random_row[0] if random_row else None


def get_video_url(video_id: int, force_refresh: bool = False, client_type: Optional[str] = None) -> VideoUrlDto:
    video_domain = None
    video: Optional[Video] = None
    normalized_client_type = str(client_type or '').strip().lower() or None
    with get_session() as session:
        video = session.get(Video, video_id)
        if not video:
            raise ValueError(f"Video with ID {video_id} not found")

        video_domain = extract_top_level_domain(video.url)

    if video_domain is None:
        raise ValueError(f"Invalid video URL: {video.url}")

    site_slug, site_info = SiteCatalog.find_site_by_domain(video_domain)
    metadata = (site_info or {}).get("metadata") or {}
    prefer_direct_urls = normalized_client_type == 'desktop'
    enable_cache = bool(metadata.get("player_url_cache"))
    cache_scope = _playback_cache_scope(normalized_client_type, prefer_direct_urls=prefer_direct_urls)
    cache_scope = f'{cache_scope}:{_auth_cache_scope(site_slug)}'

    cache_key: Optional[str] = None
    if enable_cache:
        cache_key = f"video_url:{site_slug or video_domain}:{video_id}:{cache_scope}"
        if not force_refresh:
            try:
                cached = redis_client.get(cache_key)
            except Exception:
                cached = None
            if cached:
                try:
                    payload = json.loads(cached)
                    dto = _normalize_playback_contract(VideoUrlDto.model_validate(payload), video_id=video_id)
                    return _finalize_video_url_dto(dto, prefer_direct_urls=prefer_direct_urls)
                except Exception:
                    pass

    payload = {
        'video_id': video.id,
        'url': video.url,
        'domain': video_domain,
        'title': video.title,
    }
    if normalized_client_type:
        payload['client_type'] = normalized_client_type
    if prefer_direct_urls:
        payload['direct_playback'] = True

    response = get_plugin_manager().gateway.invoke(
        'resolve_playback',
        site_name=site_slug,
        domain=video_domain,
        payload=payload,
    )
    if not response.ok:
        message = response.error.message if response.error else f'No playback handler found for domain: {video_domain}'
        error_code = getattr(response.error, 'code', None)
        if (
            error_code == RuntimeErrorCode.BAD_RESPONSE
            and message.startswith('No runtime route found for capability:')
        ):
            raise UnsupportedDomainError(message)
        raise VideoUrlExtractionError(message)

    if not isinstance(response.data, dict):
        raise TypeError('Plugin resolve_playback must return an object payload')

    dto = _normalize_playback_contract(VideoUrlDto.model_validate(response.data), video_id=video_id)

    if enable_cache and cache_key is not None:
        try:
            redis_client.setex(cache_key, VIDEO_URL_CACHE_TTL, json.dumps(dto.model_dump()))
        except Exception:
            pass

    return _finalize_video_url_dto(dto, prefer_direct_urls=prefer_direct_urls)

def _contains(column, term: str):
    return column.ilike(f'%{term}%')


def _normalize_domains(domains: Optional[List[str]]) -> list[str]:
    if not domains:
        return []

    return [
        domain for domain in {url_helper.normalize_domain(item) for item in domains if item}
        if domain
    ]
def _feed_category_predicate(user_id: int, category: str, *, video_id_column=Video.id, publish_date_column=Video.publish_date):
    published = and_(
        publish_date_column.is_not(None),
        publish_date_column <= func.now(),
    )

    if category == 'preview':
        return publish_date_column > func.now()
    if category == 'read':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == video_id_column,
                    )
                )
            ),
        )
    if category == 'unread':
        return and_(
            published,
            ~exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == video_id_column,
                    )
                )
            ),
        )
    if category == 'liked':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == video_id_column,
                        VideoInteraction.interaction_type == 1,
                    )
                )
            ),
        )
    if category == 'later':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == video_id_column,
                        VideoInteraction.interaction_type == 3,
                    )
                )
            ),
        )

    return published


def _feed_time_range_predicates(time_range: str):
    if time_range == 'all':
        return []
    now = func.now()
    if time_range == 'today':
        return [UserVideoFeed.publish_date >= func.date(now)]
    if time_range == 'week':
        start = now - timedelta(days=now.extract('dow') - 1)
        return [UserVideoFeed.publish_date >= func.date(start)]
    if time_range == 'month':
        return [
            func.extract('year', UserVideoFeed.publish_date) == func.extract('year', now),
            func.extract('month', UserVideoFeed.publish_date) == func.extract('month', now),
        ]
    if time_range == 'year':
        return [func.extract('year', UserVideoFeed.publish_date) == func.extract('year', now)]
    return []


def _build_active_subscriptions_query(
    user_id: int,
    subscription_id: Optional[int],
    nsfw: str,
    show_nsfw: bool,
    special: str,
):
    effective_nsfw = resolve_effective_nsfw_filter(nsfw, show_nsfw)
    active_subscriptions = (
        select(
            UserSubscription.subscription_id.label('subscription_id'),
            UserSubscription.is_nsfw.label('is_nsfw'),
            UserSubscription.is_special_followed.label('is_special_followed'),
            Subscription.name.label('subscription_name'),
            Subscription.type.label('subscription_type'),
        )
        .select_from(UserSubscription)
        .join(Subscription, Subscription.id == UserSubscription.subscription_id)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
    )

    if subscription_id:
        active_subscriptions = active_subscriptions.where(UserSubscription.subscription_id == subscription_id)

    if effective_nsfw == 'blocked':
        active_subscriptions = active_subscriptions.where(false())
    elif effective_nsfw == 'yes':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_nsfw.is_(True))
    elif effective_nsfw == 'no':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_nsfw.is_(False))

    if special == 'yes':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_special_followed.is_(True))
    elif special == 'no':
        active_subscriptions = active_subscriptions.where(UserSubscription.is_special_followed.is_(False))

    return active_subscriptions.subquery('active_subscriptions')


def _title_search_conditions(parsed_query, *, domain_column=Video.domain) -> list[Any]:
    conditions: list[Any] = []

    for term in parsed_query.text_terms:
        conditions.append(_contains(Video.title, term))

    for term in parsed_query.get('title'):
        conditions.append(_contains(Video.title, term))

    for term in parsed_query.get('domain'):
        conditions.append(_contains(domain_column, term))

    return conditions


def _subscription_search_query(
    *,
    active_subscriptions,
    parsed_query,
    user_id: int,
    sort_by: str,
    domains: Optional[List[str]],
    category: Optional[str],
    time_range: str,
    duration: str,
):
    subscription_query = (
        select(
            UserVideoFeed.video_id.label('video_id'),
            UserVideoFeed.publish_date.label('publish_date'),
            UserVideoFeed.video_created_at.label('video_created_at'),
            literal(60).label('search_rank'),
        )
        .select_from(active_subscriptions)
        .join(UserVideoFeed, UserVideoFeed.subscription_id == active_subscriptions.c.subscription_id)
        .join(Video, Video.id == UserVideoFeed.video_id)
        .where(
            UserVideoFeed.user_id == user_id,
            Video.is_deleted.is_(False),
        )
    )

    subscription_terms = parsed_query.get('subscription')
    text_terms = parsed_query.text_terms if not parsed_query.get('title') else []
    for term in subscription_terms + text_terms:
        subscription_query = subscription_query.where(_contains(active_subscriptions.c.subscription_name, term))

    for term in parsed_query.get('type'):
        normalized_type = normalize_subscription_type_term(term)
        if normalized_type:
            subscription_query = subscription_query.where(active_subscriptions.c.subscription_type == normalized_type)

    normalized_domains = _normalize_domains(domains)
    if normalized_domains:
        subscription_query = subscription_query.where(UserVideoFeed.domain.in_(normalized_domains))

    if category:
        subscription_query = subscription_query.where(_feed_category_predicate(
            user_id,
            category,
            video_id_column=UserVideoFeed.video_id,
            publish_date_column=UserVideoFeed.publish_date,
        ))

    for cond in _feed_time_range_predicates(time_range):
        subscription_query = subscription_query.where(cond)
    for cond in duration_predicate(duration):
        subscription_query = subscription_query.where(cond)

    feed_source = subscription_query.subquery('subscription_search_source')
    if sort_by == 'created_at':
        sort_value = func.max(feed_source.c.video_created_at).label('sort_value')
    else:
        sort_value = func.max(feed_source.c.publish_date).label('sort_value')
    search_rank = func.max(feed_source.c.search_rank).label('search_rank')

    return (
        select(
            feed_source.c.video_id,
            func.max(feed_source.c.publish_date).label('publish_date'),
            func.max(feed_source.c.video_created_at).label('video_created_at'),
            search_rank,
            sort_value,
        )
        .group_by(feed_source.c.video_id)
        .order_by(search_rank.desc(), sort_value.desc(), feed_source.c.video_id.desc())
    )


def _build_feed_rows_query(
    *,
    user_id: int,
    show_nsfw: bool,
    subscription_id: Optional[int],
    category: Optional[str],
    sort_by: str,
    nsfw: str,
    domains: Optional[List[str]],
    special: str,
):
    active_subscriptions = _build_active_subscriptions_query(
        user_id=user_id,
        subscription_id=subscription_id,
        nsfw=nsfw,
        show_nsfw=show_nsfw,
        special=special,
    )
    query_stmt = (
        select(
            UserVideoFeed.video_id.label('video_id'),
            UserVideoFeed.publish_date.label('publish_date'),
            UserVideoFeed.video_created_at.label('video_created_at'),
        )
        .select_from(UserVideoFeed)
        .join(active_subscriptions, UserVideoFeed.subscription_id == active_subscriptions.c.subscription_id)
        .join(Video, Video.id == UserVideoFeed.video_id)
        .where(
            UserVideoFeed.user_id == user_id,
            Video.is_deleted.is_(False),
        )
    )

    if category:
        query_stmt = query_stmt.where(_feed_category_predicate(
            user_id,
            category,
            video_id_column=UserVideoFeed.video_id,
            publish_date_column=UserVideoFeed.publish_date,
        ))

    normalized_domains = _normalize_domains(domains)
    if normalized_domains:
        query_stmt = query_stmt.where(UserVideoFeed.domain.in_(normalized_domains))

    if sort_by == 'created_at':
        return query_stmt.order_by(UserVideoFeed.video_created_at.desc(), UserVideoFeed.video_id.desc())
    return query_stmt.order_by(UserVideoFeed.publish_date.desc(), UserVideoFeed.video_id.desc())


def _fetch_feed_page_video_ids(session, feed_rows_query, *, offset: int, page_size: int) -> list[int]:
    video_ids: list[int] = []
    seen_video_ids: set[int] = set()
    row_offset = 0
    batch_size = max(page_size * 4, 100)

    while len(video_ids) < page_size:
        rows = session.execute(feed_rows_query.limit(batch_size).offset(row_offset)).all()
        if not rows:
            break

        row_offset += len(rows)
        for row in rows:
            if row.video_id in seen_video_ids:
                continue
            seen_video_ids.add(row.video_id)
            if len(seen_video_ids) <= offset:
                continue
            video_ids.append(row.video_id)
            if len(video_ids) >= page_size:
                break

    return video_ids


def _build_list_query(
    *,
    user_id: int,
    show_nsfw: bool,
    subscription_id: Optional[int],
    query: Optional[str],
    category: Optional[str],
    sort_by: str,
    nsfw: str,
    domains: Optional[List[str]],
    time_range: str,
    duration: str,
    content_type: str,
    special: str,
):
    active_subscriptions = _build_active_subscriptions_query(
        user_id=user_id,
        subscription_id=subscription_id,
        nsfw=nsfw,
        show_nsfw=show_nsfw,
        special=special,
    )
    parsed_query = parse_search_query(query)
    has_unsupported_terms = any([
        parsed_query.get('creator'),
        parsed_query.get('url'),
        parsed_query.get('description'),
    ])

    if parsed_query.get('subscription') or parsed_query.get('type'):
        return _subscription_search_query(
            active_subscriptions=active_subscriptions,
            parsed_query=parsed_query,
            user_id=user_id,
            sort_by=sort_by,
            domains=domains,
            category=category,
            time_range=time_range,
            duration=duration,
        )

    if has_unsupported_terms:
        return (
            select(
                Video.id.label('video_id'),
                Video.publish_date.label('publish_date'),
                Video.created_at.label('video_created_at'),
                literal(0).label('search_rank'),
                Video.publish_date.label('sort_value'),
            )
            .select_from(Video)
            .where(false())
        )

    query_stmt = (
        select(
            UserVideoFeed.video_id.label('video_id'),
            UserVideoFeed.publish_date.label('publish_date'),
            UserVideoFeed.video_created_at.label('video_created_at'),
            literal(0).label('search_rank'),
        )
        .select_from(UserVideoFeed)
        .join(active_subscriptions, UserVideoFeed.subscription_id == active_subscriptions.c.subscription_id)
        .join(Video, Video.id == UserVideoFeed.video_id)
        .where(
            UserVideoFeed.user_id == user_id,
            Video.is_deleted.is_(False),
        )
    )

    if content_type != 'all':
        query_stmt = query_stmt.where(active_subscriptions.c.subscription_type == content_type)

    if category:
        query_stmt = query_stmt.where(_feed_category_predicate(
            user_id,
            category,
            video_id_column=UserVideoFeed.video_id,
            publish_date_column=UserVideoFeed.publish_date,
        ))

    normalized_domains = _normalize_domains(domains)
    if normalized_domains:
        query_stmt = query_stmt.where(UserVideoFeed.domain.in_(normalized_domains))

    for cond in _feed_time_range_predicates(time_range):
        query_stmt = query_stmt.where(cond)
    for cond in duration_predicate(duration):
        query_stmt = query_stmt.where(cond)

    search_conditions = _title_search_conditions(parsed_query, domain_column=UserVideoFeed.domain)
    for cond in search_conditions:
        query_stmt = query_stmt.where(cond)

    feed_source = query_stmt.subquery('feed_source')
    if sort_by == 'created_at':
        sort_value = func.max(feed_source.c.video_created_at).label('sort_value')
    else:
        sort_value = func.max(feed_source.c.publish_date).label('sort_value')
    search_rank = func.max(feed_source.c.search_rank).label('search_rank')

    return (
        select(
            feed_source.c.video_id,
            func.max(feed_source.c.publish_date).label('publish_date'),
            func.max(feed_source.c.video_created_at).label('video_created_at'),
            search_rank,
            sort_value,
        )
        .group_by(feed_source.c.video_id)
        .order_by(search_rank.desc(), sort_value.desc(), feed_source.c.video_id.desc())
    )
def list_videos(
        user_id: int,
        query: str,
        subscription_id: int,
        category: str,
        sort_by: str,
        nsfw: str,
        domains: Optional[List[str]],
        page: int,
        page_size: int,
        with_total: bool = False,
        time_range: str = 'all',
        duration: str = 'all',
        content_type: str = 'all',
        special: str = 'all',
) -> Tuple[List[dict], Optional[int]]:
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)
    offset = max((page - 1) * page_size, 0)
    started_at = perf_counter()

    with get_session() as session:
        build_query_started_at = perf_counter()
        use_feed_row_pagination = (
            not query
            and duration == 'all'
            and time_range == 'all'
            and content_type == 'all'
            and category in (None, 'all', 'preview')
        )
        if use_feed_row_pagination:
            base_ids_query = _build_feed_rows_query(
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
            base_ids_query = _build_list_query(
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
            )
        build_query_ms = _elapsed_ms(build_query_started_at)

        video_ids_started_at = perf_counter()
        if use_feed_row_pagination:
            video_ids = _fetch_feed_page_video_ids(session, base_ids_query, offset=offset, page_size=page_size)
        else:
            video_ids = [
                row.video_id
                for row in session.execute(
                    base_ids_query
                    .limit(page_size)
                    .offset(offset)
                ).all()
            ]
        video_ids_ms = _elapsed_ms(video_ids_started_at)

        total_count = None
        if with_total:
            total_count_started_at = perf_counter()
            count_source = base_ids_query.order_by(None).subquery()
            if use_feed_row_pagination:
                total_count = session.execute(
                    select(func.count(func.distinct(count_source.c.video_id))).select_from(count_source)
                ).scalar() or 0
            else:
                total_count = session.execute(
                    select(func.count()).select_from(count_source)
                ).scalar() or 0
            total_count_ms = _elapsed_ms(total_count_started_at)
        else:
            total_count_ms = 0.0

        if not video_ids:
            logger.info(
                '[Performance] list_videos user_id=%s category=%s page=%s page_size=%s query=%s nsfw=%s domains=%s '
                'video_count=0 build_query_ms=%.3f video_ids_ms=%.3f total_count_ms=%.3f total_ms=%.3f',
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
                _elapsed_ms(started_at),
            )
            return [], total_count

        videos_started_at = perf_counter()
        order_case = case(
            {video_id: index for index, video_id in enumerate(video_ids)},
            value=Video.id
        )

        videos = session.scalars(
            select(Video)
            .where(Video.id.in_(video_ids))
            .order_by(order_case)
        ).all()
        video_map = {video.id: video for video in videos}
        videos_ms = _elapsed_ms(videos_started_at)

        history_started_at = perf_counter()
        history_rows = session.execute(
            select(VideoHistory.video_id, VideoHistory.last_position).where(
                VideoHistory.user_id == user_id,
                VideoHistory.video_id.in_(video_ids),
            )
        ).all()
        history_map = {row.video_id: row.last_position for row in history_rows}
        history_ms = _elapsed_ms(history_started_at)

        subscriptions_started_at = perf_counter()
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
            .order_by(SubscriptionVideo.video_id.asc(), Subscription.id.asc())
        ).all()
        subscriptions_map: Dict[int, List[dict]] = {}
        seen_subscription_keys = set()
        for row in subscription_rows:
            key = (row.video_id, row.id)
            if key in seen_subscription_keys:
                continue
            seen_subscription_keys.add(key)
            subscriptions_map.setdefault(row.video_id, []).append({
                'id': row.id,
                'name': row.name,
                'url': row.url,
                'type': row.type,
                'avatar': row.avatar,
                'is_nsfw': row.is_nsfw,
                'is_special_followed': row.is_special_followed,
            })
        subscriptions_ms = _elapsed_ms(subscriptions_started_at)

        creators_started_at = perf_counter()
        creator_rows = session.execute(
            select(VideoCreator.video_id, Creator)
            .join(Creator, Creator.id == VideoCreator.creator_id)
            .where(
                VideoCreator.video_id.in_(video_ids),
                Creator.is_deleted.is_(False),
            )
            .order_by(VideoCreator.video_id.asc(), Creator.id.asc())
        ).all()
        actors_map: Dict[int, List[dict]] = {}
        for video_id, creator in creator_rows:
            actors_map.setdefault(video_id, []).append(creator.to_dict())
        creators_ms = _elapsed_ms(creators_started_at)

        thumbnails_started_at = perf_counter()
        thumbnail_map = thumbnail_downloader_service.get_thumbnail_url_map([
            (video.id, video.thumbnail, video.url)
            for video_id in video_ids
            for video in [video_map.get(video_id)]
            if video is not None
        ])
        thumbnails_ms = _elapsed_ms(thumbnails_started_at)

        assemble_started_at = perf_counter()
        video_list = []
        for video_id in video_ids:
            video = video_map.get(video_id)
            if not video:
                continue
            video_data = {
                'id': video.id,
                'title': video.title,
                'url': video.url,
                'thumbnail': thumbnail_map.get(video.id),
                'duration': video.duration,
                'last_position': history_map.get(video.id, 0),
                'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
                'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'subscriptions': _merge_profiles(
                    subscriptions_map.get(video.id, []),
                    _video_extra_profiles(video, 'subscriptions'),
                ),
                'actors': _merge_profiles(
                    actors_map.get(video.id, []),
                    _video_extra_profiles(video, 'actors'),
                ),
            }
            video_list.append(video_data)
        assemble_ms = _elapsed_ms(assemble_started_at)
        total_ms = _elapsed_ms(started_at)

        logger.info(
            '[Performance] list_videos user_id=%s category=%s page=%s page_size=%s query=%s nsfw=%s domains=%s '
            'video_count=%s build_query_ms=%.3f video_ids_ms=%.3f total_count_ms=%.3f videos_ms=%.3f '
            'history_ms=%.3f subscriptions_ms=%.3f creators_ms=%.3f thumbnails_ms=%.3f assemble_ms=%.3f total_ms=%.3f',
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
            videos_ms,
            history_ms,
            subscriptions_ms,
            creators_ms,
            thumbnails_ms,
            assemble_ms,
            total_ms,
        )

        return video_list, total_count

def get_video(user_id, video_id):
    with get_session() as session:
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
                        UserSubscription.is_deleted == False
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
            )
        ).first()
        if not video:
            return None

        subscription_ids = {link.subscription_id for link in video.subscription_links}
        counts_map = {}
        if subscription_ids:
            rows = session.execute(
                select(SubscriptionVideo.subscription_id, func.count(SubscriptionVideo.video_id).label('video_count'))
                .where(SubscriptionVideo.subscription_id.in_(list(subscription_ids)))
                .group_by(SubscriptionVideo.subscription_id)
            ).all()
            counts_map = {row[0]: row[1] for row in rows}

        subscriptions_data = []
        for link in video.subscription_links:
            subscription = link.subscription
            if not subscription:
                continue
            user_subscriptions = subscription.user_subscriptions or []
            if not user_subscriptions:
                continue
            user_subscription = user_subscriptions[0]
            s_dict = subscription.to_dict()
            s_dict['total_extract'] = counts_map.get(subscription.id, 0)
            s_dict['total_videos'] = max(int(s_dict.get('total_videos') or 0), s_dict['total_extract'])
            s_dict['is_nsfw'] = user_subscription.is_nsfw
            subscriptions_data.append(s_dict)

        def _history_sort_key(history: VideoHistory):
            return history.updated_at or history.end_time or history.created_at

        def _interaction_sort_key(interaction: VideoInteraction):
            return interaction.updated_at or interaction.created_at

        video_history = max(video.histories, key=_history_sort_key, default=None)
        video_interaction = max(video.interactions, key=_interaction_sort_key, default=None)
        try:
            clip_markers = session.scalars(
                select(VideoClipMarker)
                .where(
                    VideoClipMarker.user_id == user_id,
                    VideoClipMarker.video_id == video_id,
                )
                .order_by(VideoClipMarker.start_time.asc(), VideoClipMarker.created_at.asc(), VideoClipMarker.id.asc())
            ).all()
        except OperationalError:
            logger.warning('[video_service] video_clip_marker table is unavailable; falling back to empty clip markers')
            clip_markers = []

        video_data = {
            **video.to_dict(),
            'thumbnail': thumbnail_downloader_service.get_thumbnail_url(video.id, video.thumbnail, video.url),
            'interaction_type': video_interaction.interaction_type if video_interaction else None,
            'last_position': video_history.last_position if video_history else 0,
            'domain': url_helper.extract_top_level_domain(video.url),
            'subscriptions': _merge_profiles(subscriptions_data, _video_extra_profiles(video, 'subscriptions')),
            'actors': _merge_profiles(
                [creator.to_dict() for creator in video.creators],
                _video_extra_profiles(video, 'actors'),
            ),
            'creators': [creator.to_dict() for creator in video.creators],
            'clip_markers': [serialize_marker(marker) for marker in clip_markers],
        }

        return video_data
