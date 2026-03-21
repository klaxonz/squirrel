import json
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload, with_loader_criteria
from core.database import get_session
from services.video_query import build_base_video_query, build_video_count_source_query, category_predicate, resolve_sort_column


from core.exceptions.video_exceptions import UnsupportedDomainError
from crawl import VideoUrlHandler, get_handler_registry

from models.links import SubscriptionVideo, UserSubscription

from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from schemas.video.dto.video_dto import VideoExtractDto, VideoUrlDto

from services import download_service, subscription_video_service, user_config_service
from utils import url_helper
from utils.url_helper import extract_top_level_domain
from utils.site_catalog import SiteCatalog
from core.cache import redis_client
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service

logger = logging.getLogger()

VIDEO_URL_CACHE_TTL = 300


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
) -> Optional[Video]:
    """返回符合过滤条件的一个随机视频（已发布）。

    - 遵循用户 NSFW 偏好（通过 user_config）
    - 支持分类：all/read/unread/preview/liked/later（与列表页一致）
    - 支持 subscription/site(query by domains)/keyword 过滤
    """
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    # 基础可重用查询
    base = build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
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


def get_video_url(video_id: int, force_refresh: bool = False) -> VideoUrlDto:
    video_domain = None
    video: Optional[Video] = None
    with get_session() as session:
        video = session.get(Video, video_id)
        if not video:
            raise ValueError(f"Video with ID {video_id} not found")

        video_domain = extract_top_level_domain(video.url)

    if video_domain is None:
        raise ValueError(f"Invalid video URL: {video.url}")

    site_slug, site_info = SiteCatalog.find_site_by_domain(video_domain)
    metadata = (site_info or {}).get("metadata") or {}
    enable_cache = bool(metadata.get("player_url_cache"))

    cache_key: Optional[str] = None
    if enable_cache:
        cache_key = f"video_url:{site_slug or video_domain}:{video_id}"
        if not force_refresh:
            try:
                cached = redis_client.get(cache_key)
            except Exception:
                cached = None
            if cached:
                try:
                    payload = json.loads(cached)
                    return VideoUrlDto.model_validate(payload)
                except Exception:
                    pass

    handler_registry = get_handler_registry()
    handler_key = handler_registry.get_by_domain(video_domain)
    if not handler_key:
        raise UnsupportedDomainError(f"No handler found for domain: {video_domain}")
    handler_plugin = handler_registry.get(handler_key)
    if not handler_plugin:
        raise UnsupportedDomainError(f"No handler found for domain: {video_domain}")
    # handler_plugin 可能是类或实例
    if isinstance(handler_plugin, type):
        handler: VideoUrlHandler = handler_plugin()
    else:
        handler: VideoUrlHandler = handler_plugin
    result = handler.get_video_url(video)

    if not isinstance(result, dict):
        raise TypeError("Handler.get_video_url must return a dict")

    dto = VideoUrlDto.model_validate(result)

    if enable_cache and cache_key is not None:
        try:
            redis_client.setex(cache_key, VIDEO_URL_CACHE_TTL, json.dumps(dto.model_dump()))
        except Exception:
            pass

    return dto



def _get_video_counts_in_session(session, user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                                 query: Optional[str] = None, nsfw: str = 'all', domains: Optional[List[str]] = None):
    """获取各类别视频数量 - 统一与列表筛选逻辑"""
    candidate_videos = (
        build_video_count_source_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
        .cte('candidate_videos')
    )

    published = candidate_videos.c.publish_date <= func.now()
    preview = candidate_videos.c.publish_date > func.now()
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

    row = session.execute(count_query).first()
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
        domains: Optional[List[str]]
) -> dict:
    """获取视频各类别计数（独立接口）"""
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    with get_session() as session:
        return _get_video_counts_in_session(session, user_id, show_nsfw, subscription_id, query, nsfw, domains)


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
) -> Tuple[List[dict], Optional[int]]:
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    with get_session() as session:
        base_query = build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
        base_query = base_query.where(category_predicate(user_id, category))

        order_column = resolve_sort_column(sort_by).desc()


        base_ids_query = (
            base_query
            .with_only_columns(Video.id, order_column)
            .distinct()
            .order_by(order_column)
        )

        id_rows = session.execute(
            base_ids_query
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        video_ids = [row[0] for row in id_rows]

        total_count = None
        if with_total:
            total_count = session.execute(
                select(func.count()).select_from(
                    base_ids_query
                    .with_only_columns(Video.id)
                    .order_by(None)
                    .subquery()
                )
            ).scalar() or 0

        if not video_ids:
            return [], total_count

        order_case = case(
            {video_id: index for index, video_id in enumerate(video_ids)},
            value=Video.id
        )

        videos = session.scalars(
            select(Video)
            .where(Video.id.in_(video_ids))
            .options(
                selectinload(Video.subscription_links)
                .selectinload(SubscriptionVideo.subscription)
                .selectinload(Subscription.user_subscriptions),
                selectinload(Video.creators),
                selectinload(Video.histories),
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
            )
            .order_by(order_case)
        ).all()

        def _history_sort_key(history: VideoHistory):
            return history.updated_at or history.end_time or history.created_at

        video_list = []
        for video in videos:
            subscriptions_list = []
            for link in video.subscription_links:
                subscription = link.subscription
                if not subscription:
                    continue
                user_subscriptions = subscription.user_subscriptions or []
                if not user_subscriptions:
                    continue
                user_subscription = user_subscriptions[0]
                subscriptions_list.append({
                    'id': subscription.id,
                    'name': subscription.name,
                    'url': subscription.url,
                    'type': subscription.type,
                    'avatar': subscription.avatar,
                    'is_nsfw': user_subscription.is_nsfw
                })

            history = max(video.histories, key=_history_sort_key, default=None)

            video_data = {
                'id': video.id,
                'title': video.title,
                'url': video.url,
                'thumbnail': thumbnail_downloader_service.get_thumbnail_url(video.id, video.thumbnail, video.url),
                'duration': video.duration,
                'last_position': history.last_position if history else 0,
                'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
                'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'subscriptions': subscriptions_list,
                'actors': [creator.to_dict() for creator in video.creators]
            }
            video_list.append(video_data)

        return video_list, total_count



def download_video(video_id: int):
    video = get_video_by_id(video_id)
    subscription_video = subscription_video_service.get_subscription_video_by_video_id(video_id)
    if not video:
        raise ValueError("Video not found")
    params = VideoExtractDto(
        url=video.url,
        only_extract=False,
        subscribed=True,
        subscription_id=subscription_video.subscription_id
    )
    download_service.enqueue_video_extraction(params)


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
            s_dict['is_nsfw'] = user_subscription.is_nsfw
            subscriptions_data.append(s_dict)

        def _history_sort_key(history: VideoHistory):
            return history.updated_at or history.end_time or history.created_at

        def _interaction_sort_key(interaction: VideoInteraction):
            return interaction.updated_at or interaction.created_at

        video_history = max(video.histories, key=_history_sort_key, default=None)
        video_interaction = max(video.interactions, key=_interaction_sort_key, default=None)

        video_data = {
            **video.to_dict(),
            'thumbnail': thumbnail_downloader_service.get_thumbnail_url(video.id, video.thumbnail, video.url),
            'interaction_type': video_interaction.interaction_type if video_interaction else None,
            'last_position': video_history.last_position if video_history else 0,
            'domain': url_helper.extract_top_level_domain(video.url),
            'subscriptions': subscriptions_data,
            'creators': [creator.to_dict() for creator in video.creators]
        }

        return video_data

