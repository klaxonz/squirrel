import json
import logging
from datetime import datetime
import hashlib
from time import perf_counter
from typing import List, Tuple, Optional, Dict
from urllib.parse import parse_qs, urlencode, urlparse
from crawl.runtime_errors import RuntimeErrorCode
from sqlalchemy import select, func, and_, case, exists, false
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload, with_loader_criteria
from core.database import get_session
from services.video_query import (
    build_base_video_query,
    build_video_count_source_query,
    build_video_search_clauses,
    category_predicate,
    resolve_sort_column,
    time_range_predicate,
    duration_predicate,
    content_type_predicate,
)


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



def _get_video_counts_in_session(session, user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                                 query: Optional[str] = None, nsfw: str = 'all', domains: Optional[List[str]] = None,
                                 time_range: str = 'all', duration: str = 'all', content_type: str = 'all'):
    """获取各类别视频数量 - 基于实时 feed 表统计"""
    started_at = perf_counter()
    candidate_videos = (
        _build_feed_query(
            user_id=user_id,
            show_nsfw=show_nsfw,
            subscription_id=subscription_id,
            query=query,
            category=None,
            sort_by='publish_date',
            nsfw=nsfw,
            domains=domains,
            time_range=time_range,
            duration=duration,
            content_type=content_type,
        )
        .order_by(None)
        .subquery('candidate_videos')
    )
    candidate_query_ms = _elapsed_ms(started_at)

    published = candidate_videos.c.publish_date <= func.now()
    preview = candidate_videos.c.publish_date > func.now()
    cte_started_at = perf_counter()
    read_videos = (
        select(VideoHistory.video_id.label('video_id'))
        .where(VideoHistory.user_id == user_id)
        .group_by(VideoHistory.video_id)
        .cte('read_videos')
    )
    liked_videos = (
        select(VideoInteraction.video_id.label('video_id'))
        .where(
            and_(
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 1
            )
        )
        .group_by(VideoInteraction.video_id)
        .cte('liked_videos')
    )
    later_videos = (
        select(VideoInteraction.video_id.label('video_id'))
        .where(
            and_(
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 3
            )
        )
        .group_by(VideoInteraction.video_id)
        .cte('later_videos')
    )
    cte_build_ms = _elapsed_ms(cte_started_at)
    count_query_started_at = perf_counter()
    count_query = (
        select(
            func.count().filter(published).label('all_count'),
            func.count().filter(preview).label('preview_count'),
            func.count().filter(and_(published, read_videos.c.video_id.is_not(None))).label('read_count'),
            func.count().filter(and_(published, liked_videos.c.video_id.is_not(None))).label('liked_count'),
            func.count().filter(and_(published, later_videos.c.video_id.is_not(None))).label('later_count'),
        )
        .select_from(candidate_videos)
        .outerjoin(read_videos, read_videos.c.video_id == candidate_videos.c.video_id)
        .outerjoin(liked_videos, liked_videos.c.video_id == candidate_videos.c.video_id)
        .outerjoin(later_videos, later_videos.c.video_id == candidate_videos.c.video_id)
    )
    count_query_build_ms = _elapsed_ms(count_query_started_at)

    execute_started_at = perf_counter()
    row = session.execute(count_query).first()
    execute_ms = _elapsed_ms(execute_started_at)
    total_ms = _elapsed_ms(started_at)

    logger.info(
        '[Performance] get_video_counts user_id=%s subscription_id=%s query=%s nsfw=%s domains=%s '
        'candidate_query_ms=%.3f cte_build_ms=%.3f count_query_build_ms=%.3f execute_ms=%.3f total_ms=%.3f',
        user_id,
        subscription_id,
        bool(query),
        nsfw,
        len(domains or []),
        candidate_query_ms,
        cte_build_ms,
        count_query_build_ms,
        execute_ms,
        total_ms,
    )

    if not row:
        return {
            "all": 0,
            "read": 0,
            "unread": 0,
            "preview": 0,
            "liked": 0,
            "later": 0
        }

    all_count = row.all_count or 0
    preview_count = row.preview_count or 0
    read_count = row.read_count or 0
    liked_count = row.liked_count or 0
    later_count = row.later_count or 0
    unread_count = max(all_count - read_count, 0)

    return {
        "all": all_count,
        "read": read_count,
        "unread": unread_count,
        "preview": preview_count,
        "liked": liked_count,
        "later": later_count
    }




def get_video_counts(
        user_id: int,
        query: str,
        subscription_id: int,
        nsfw: str,
        domains: Optional[List[str]],
        time_range: str = 'all',
        duration: str = 'all',
        content_type: str = 'all',
) -> dict:
    """获取视频各类别计数（独立接口）"""
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    with get_session() as session:
        return _get_video_counts_in_session(
            session, user_id, show_nsfw, subscription_id, query, nsfw, domains,
            time_range, duration, content_type,
        )


def _feed_sort_column(sort_by: str):
    if sort_by == 'created_at':
        return UserVideoFeed.video_created_at
    return UserVideoFeed.publish_date


def _feed_category_predicate(user_id: int, category: str):
    published = and_(
        UserVideoFeed.publish_date.is_not(None),
        UserVideoFeed.publish_date <= func.now(),
    )

    if category == 'preview':
        return UserVideoFeed.publish_date > func.now()
    if category == 'read':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == UserVideoFeed.video_id,
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
                        VideoHistory.video_id == UserVideoFeed.video_id,
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
                        VideoInteraction.video_id == UserVideoFeed.video_id,
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
                        VideoInteraction.video_id == UserVideoFeed.video_id,
                        VideoInteraction.interaction_type == 3,
                    )
                )
            ),
        )

    return published


def _build_feed_query(
    user_id: int,
    show_nsfw: bool,
    subscription_id: Optional[int],
    query: Optional[str],
    category: Optional[str],
    sort_by: str,
    nsfw: str,
    domains: Optional[List[str]],
    time_range: str = 'all',
    duration: str = 'all',
    content_type: str = 'all',
):
    effective_nsfw = resolve_effective_nsfw_filter(nsfw, show_nsfw)
    feed_query = select(
        UserVideoFeed.video_id.label('video_id'),
        UserVideoFeed.publish_date.label('publish_date'),
        UserVideoFeed.video_created_at.label('video_created_at'),
    ).where(
        UserVideoFeed.user_id == user_id,
    )

    if subscription_id:
        feed_query = feed_query.where(UserVideoFeed.subscription_id == subscription_id)

    if effective_nsfw == 'blocked':
        feed_query = feed_query.where(false())
    elif effective_nsfw == 'yes':
        feed_query = feed_query.where(UserVideoFeed.is_nsfw.is_(True))
    elif effective_nsfw == 'no':
        feed_query = feed_query.where(UserVideoFeed.is_nsfw.is_(False))

    if domains:
        normalized_domains = [
            domain for domain in {url_helper.normalize_domain(item) for item in domains if item} if domain
        ]
        if normalized_domains:
            feed_query = feed_query.where(UserVideoFeed.domain.in_(normalized_domains))

    search_clauses = build_video_search_clauses(
        user_id=user_id,
        query=query,
        video_id_column=UserVideoFeed.video_id,
        subscription_id_column=UserVideoFeed.subscription_id,
    )
    if search_clauses:
        feed_query = feed_query.join(Video, Video.id == UserVideoFeed.video_id).where(
            Video.is_deleted.is_(False),
            *search_clauses,
        )

    if category:
        feed_query = feed_query.where(_feed_category_predicate(user_id, category))

    # Collect Video-level conditions (time_range, duration)
    video_conds = []
    video_conds.extend(time_range_predicate(time_range))
    video_conds.extend(duration_predicate(duration))
    # Collect Subscription-level conditions (content_type)
    type_conds = content_type_predicate(content_type)

    needs_subscription_join = bool(type_conds)
    needs_video_join = bool(video_conds) or needs_subscription_join

    if search_clauses:
        # Video already joined above; add remaining Video conditions and Subscription conditions
        if needs_subscription_join:
            feed_query = feed_query.join(
                SubscriptionVideo,
                SubscriptionVideo.video_id == UserVideoFeed.video_id,
            ).join(
                Subscription,
                Subscription.id == SubscriptionVideo.subscription_id,
            )
        for cond in type_conds:
            feed_query = feed_query.where(cond)
        for cond in video_conds:
            feed_query = feed_query.where(cond)
    elif needs_video_join:
        # Video not yet joined; join once and apply all conditions
        if needs_subscription_join:
            feed_query = feed_query.join(
                SubscriptionVideo,
                SubscriptionVideo.video_id == UserVideoFeed.video_id,
            ).join(
                Subscription,
                Subscription.id == SubscriptionVideo.subscription_id,
            )
        feed_query = feed_query.join(Video, Video.id == UserVideoFeed.video_id)
        for cond in type_conds:
            feed_query = feed_query.where(cond)
        for cond in video_conds:
            feed_query = feed_query.where(cond)

    feed_source = feed_query.subquery()
    if sort_by == 'created_at':
        sort_value = func.max(feed_source.c.video_created_at).label('sort_value')
    else:
        sort_value = func.max(feed_source.c.publish_date).label('sort_value')

    return (
        select(
            feed_source.c.video_id,
            func.max(feed_source.c.publish_date).label('publish_date'),
            func.max(feed_source.c.video_created_at).label('video_created_at'),
            sort_value,
        )
        .group_by(feed_source.c.video_id)
        .order_by(sort_value.desc(), feed_source.c.video_id.desc())
    )


def _build_ordered_feed_query(
    user_id: int,
    show_nsfw: bool,
    subscription_id: Optional[int],
    query: Optional[str],
    category: Optional[str],
    sort_by: str,
    nsfw: str,
    domains: Optional[List[str]],
    time_range: str = 'all',
    duration: str = 'all',
    content_type: str = 'all',
):
    effective_nsfw = resolve_effective_nsfw_filter(nsfw, show_nsfw)
    feed_query = select(
        UserVideoFeed.video_id.label('video_id'),
        UserVideoFeed.publish_date.label('publish_date'),
        UserVideoFeed.video_created_at.label('video_created_at'),
    ).where(
        UserVideoFeed.user_id == user_id,
    )

    if subscription_id:
        feed_query = feed_query.where(UserVideoFeed.subscription_id == subscription_id)

    if effective_nsfw == 'blocked':
        feed_query = feed_query.where(false())
    elif effective_nsfw == 'yes':
        feed_query = feed_query.where(UserVideoFeed.is_nsfw.is_(True))
    elif effective_nsfw == 'no':
        feed_query = feed_query.where(UserVideoFeed.is_nsfw.is_(False))

    if domains:
        normalized_domains = [
            domain for domain in {url_helper.normalize_domain(item) for item in domains if item} if domain
        ]
        if normalized_domains:
            feed_query = feed_query.where(UserVideoFeed.domain.in_(normalized_domains))

    search_clauses = build_video_search_clauses(
        user_id=user_id,
        query=query,
        video_id_column=UserVideoFeed.video_id,
        subscription_id_column=UserVideoFeed.subscription_id,
    )
    if search_clauses:
        feed_query = feed_query.join(Video, Video.id == UserVideoFeed.video_id).where(
            Video.is_deleted.is_(False),
            *search_clauses,
        )

    if category:
        feed_query = feed_query.where(_feed_category_predicate(user_id, category))

    video_conds = []
    video_conds.extend(time_range_predicate(time_range))
    video_conds.extend(duration_predicate(duration))
    type_conds = content_type_predicate(content_type)

    needs_subscription_join = bool(type_conds)
    needs_video_join = bool(video_conds) or needs_subscription_join

    if search_clauses:
        if needs_subscription_join:
            feed_query = feed_query.join(
                SubscriptionVideo,
                SubscriptionVideo.video_id == UserVideoFeed.video_id,
            ).join(
                Subscription,
                Subscription.id == SubscriptionVideo.subscription_id,
            )
        for cond in type_conds:
            feed_query = feed_query.where(cond)
        for cond in video_conds:
            feed_query = feed_query.where(cond)
    elif needs_video_join:
        if needs_subscription_join:
            feed_query = feed_query.join(
                SubscriptionVideo,
                SubscriptionVideo.video_id == UserVideoFeed.video_id,
            ).join(
                Subscription,
                Subscription.id == SubscriptionVideo.subscription_id,
            )
        feed_query = feed_query.join(Video, Video.id == UserVideoFeed.video_id)
        for cond in type_conds:
            feed_query = feed_query.where(cond)
        for cond in video_conds:
            feed_query = feed_query.where(cond)

    sort_column = _feed_sort_column(sort_by)
    return feed_query.order_by(sort_column.desc(), UserVideoFeed.video_id.desc())


def _collect_feed_page_video_ids(session, ordered_feed_query, page: int, page_size: int) -> List[int]:
    target_start = max((page - 1) * page_size, 0)
    target_end = target_start + page_size
    batch_size = min(max(page_size * 4, target_end + page_size, 200), 2000)
    raw_offset = 0
    seen_video_ids = set()
    ordered_video_ids: List[int] = []

    while len(ordered_video_ids) < target_end:
        rows = session.execute(
            ordered_feed_query
            .limit(batch_size)
            .offset(raw_offset)
        ).all()
        if not rows:
            break

        raw_offset += len(rows)
        for row in rows:
            video_id = row.video_id
            if video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)
            ordered_video_ids.append(video_id)
            if len(ordered_video_ids) >= target_end:
                break

        if len(rows) < batch_size:
            break

    return ordered_video_ids[target_start:target_end]


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
) -> Tuple[List[dict], Optional[int]]:
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)
    offset = max((page - 1) * page_size, 0)
    started_at = perf_counter()

    with get_session() as session:
        build_query_started_at = perf_counter()
        base_ids_query = _build_feed_query(
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
        )
        build_query_ms = _elapsed_ms(build_query_started_at)

        video_ids_started_at = perf_counter()
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
            total_count = session.execute(
                select(func.count()).select_from(base_ids_query.order_by(None).subquery())
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
                UserVideoFeed.video_id,
                Subscription.id,
                Subscription.name,
                Subscription.url,
                Subscription.type,
                Subscription.avatar,
                UserVideoFeed.is_nsfw,
            )
            .join(Subscription, Subscription.id == UserVideoFeed.subscription_id)
            .where(
                UserVideoFeed.user_id == user_id,
                UserVideoFeed.video_id.in_(video_ids),
                Subscription.is_deleted.is_(False),
            )
            .order_by(UserVideoFeed.video_id.asc(), Subscription.id.asc())
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
                'subscriptions': subscriptions_map.get(video.id, []),
                'actors': actors_map.get(video.id, []),
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
            'subscriptions': subscriptions_data,
            'creators': [creator.to_dict() for creator in video.creators],
            'clip_markers': [serialize_marker(marker) for marker in clip_markers],
        }

        return video_data
