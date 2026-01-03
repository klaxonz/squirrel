import json
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from sqlalchemy import select, func, and_, or_
from core.database import get_session
from core.exceptions.video_exceptions import UnsupportedDomainError
from crawl import VideoUrlHandler, get_handler_registry

from models.creator import Creator
from models.links import VideoCreator, SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from schemas.video.dto.video_dto import VideoExtractDto, VideoDto, VideoUrlDto
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
    base = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)

    # 类别条件
    if category == 'read':
        base = base.join(VideoHistory, and_(
            VideoHistory.video_id == Video.id,
            VideoHistory.user_id == user_id
        )).where(Video.publish_date <= func.now())
    elif category == 'unread':
        base = base.outerjoin(VideoHistory, and_(
            VideoHistory.video_id == Video.id,
            VideoHistory.user_id == user_id
        )).where(and_(VideoHistory.video_id.is_(None), Video.publish_date <= func.now()))
    elif category == 'preview':
        base = base.where(Video.publish_date > func.now())
    elif category == 'liked':
        base = base.join(VideoInteraction, and_(
            VideoInteraction.video_id == Video.id,
            VideoInteraction.user_id == user_id,
            VideoInteraction.interaction_type == 1
        )).where(Video.publish_date <= func.now())
    elif category == 'later':
        base = base.join(VideoInteraction, and_(
            VideoInteraction.video_id == Video.id,
            VideoInteraction.user_id == user_id,
            VideoInteraction.interaction_type == 3
        )).where(Video.publish_date <= func.now())
    else:
        base = base.where(Video.publish_date <= func.now())

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


def _build_base_video_query(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                            query: Optional[str] = None, nsfw: str = 'all', domains: Optional[List[str]] = None):
    """构建基础视频查询，以Video为主表"""
    base_query = (
        select(Video, SubscriptionVideo.subscription_id.label('subscription_id'))
        .select_from(Video)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            and_(
                Video.is_deleted == False,
                UserSubscription.is_deleted == False,
                Subscription.is_deleted == False,
                UserSubscription.user_id == user_id
            )
        )
    )

    if subscription_id:
        base_query = base_query.where(SubscriptionVideo.subscription_id == subscription_id)

    # NSFW 过滤逻辑（方案A）
    if nsfw == 'yes':
        base_query = base_query.where(UserSubscription.is_nsfw == True)
    elif nsfw == 'no':
        base_query = base_query.where(UserSubscription.is_nsfw == False)
    else:
        # nsfw == 'all' 且遵循用户偏好
        if not show_nsfw:
            base_query = base_query.where(UserSubscription.is_nsfw == False)

    if query:
        base_query = base_query.where(Video.title.like(f"%{query}%"))

    # 域名过滤：根据 URL 中包含的域名片段进行过滤
    if domains:
        like_clauses = [Video.url.like(f"%{d}%") for d in domains if d]
        if like_clauses:
            base_query = base_query.where(or_(*like_clauses))

    return base_query


def _query_all_videos(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None, query: Optional[str] = None,
                      sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all',
                      domains: Optional[List[str]] = None):
    """查询所有视频（排除预览视频）"""
    base_query = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
    base_query = base_query.where(Video.publish_date <= func.now())

    if sort_by == 'created_at':
        base_query = base_query.order_by(Video.created_at.desc())
    else:
        base_query = base_query.order_by(Video.publish_date.desc())

    base_query = base_query.limit(page_size).offset((page - 1) * page_size)
    return base_query


def _query_read_videos(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                       query: Optional[str] = None,
                       sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all',
                       domains: Optional[List[str]] = None):
    """查询已读视频"""
    base_query = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
    base_query = base_query.join(VideoHistory, and_(
        VideoHistory.video_id == Video.id,
        VideoHistory.user_id == user_id
    )).where(Video.publish_date <= func.now())

    if sort_by == 'created_at':
        base_query = base_query.order_by(Video.created_at.desc())
    else:
        base_query = base_query.order_by(Video.publish_date.desc())

    base_query = base_query.limit(page_size).offset((page - 1) * page_size)
    return base_query


def _query_unread_videos(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                         query: Optional[str] = None,
                         sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all',
                         domains: Optional[List[str]] = None):
    """查询未读视频"""
    base_query = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
    base_query = base_query.outerjoin(VideoHistory, and_(
        VideoHistory.video_id == Video.id,
        VideoHistory.user_id == user_id
    )).where(
        and_(
            VideoHistory.video_id.is_(None),
            Video.publish_date <= func.now()
        )
    )

    if sort_by == 'created_at':
        base_query = base_query.order_by(Video.created_at.desc())
    else:
        base_query = base_query.order_by(Video.publish_date.desc())

    base_query = base_query.limit(page_size).offset((page - 1) * page_size)
    return base_query


def _query_preview_videos(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                          query: Optional[str] = None,
                          sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all',
                          domains: Optional[List[str]] = None):
    """查询预览视频"""
    base_query = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
    base_query = base_query.where(Video.publish_date > func.now())

    if sort_by == 'created_at':
        base_query = base_query.order_by(Video.created_at.desc())
    else:
        base_query = base_query.order_by(Video.publish_date.desc())

    base_query = base_query.limit(page_size).offset((page - 1) * page_size)
    return base_query


def _query_liked_videos(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                        query: Optional[str] = None,
                        sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all',
                        domains: Optional[List[str]] = None):
    """查询点赞视频"""
    base_query = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
    base_query = base_query.join(VideoInteraction, and_(
        VideoInteraction.video_id == Video.id,
        VideoInteraction.user_id == user_id,
        VideoInteraction.interaction_type == 1
    )).where(Video.publish_date <= func.now())

    if sort_by == 'created_at':
        base_query = base_query.order_by(Video.created_at.desc())
    else:
        base_query = base_query.order_by(Video.publish_date.desc())

    base_query = base_query.limit(page_size).offset((page - 1) * page_size)
    return base_query


def _query_later_videos(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                        query: Optional[str] = None,
                        sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all',
                        domains: Optional[List[str]] = None):
    """查询稍后观看视频（interaction_type=3）"""
    base_query = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)
    base_query = base_query.join(VideoInteraction, and_(
        VideoInteraction.video_id == Video.id,
        VideoInteraction.user_id == user_id,
        VideoInteraction.interaction_type == 3
    )).where(Video.publish_date <= func.now())

    if sort_by == 'created_at':
        base_query = base_query.order_by(Video.created_at.desc())
    else:
        base_query = base_query.order_by(Video.publish_date.desc())

    base_query = base_query.limit(page_size).offset((page - 1) * page_size)
    return base_query


def _get_category_count(user_id: int, show_nsfw: bool, category: str, subscription_id: Optional[int] = None,
                        query: Optional[str] = None, nsfw: str = 'all', domains: Optional[List[str]] = None) -> int:
    """获取特定类别的视频数量，优化的count查询"""
    with get_session() as session:
        # 基础count查询，只选择Video.id用于计数
        base_count_query = (
            select(func.count(func.distinct(Video.id)))
            .select_from(Video)
            .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
            .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
            .join(Subscription, UserSubscription.subscription_id == Subscription.id)
            .where(
                and_(
                    Video.is_deleted == False,
                    UserSubscription.is_deleted == False,
                    Subscription.is_deleted == False,
                    UserSubscription.user_id == user_id
                )
            )
        )

        # 根据类别添加特定的JOIN和条件
        if category == 'read':
            base_count_query = base_count_query.join(VideoHistory, and_(
                VideoHistory.video_id == Video.id,
                VideoHistory.user_id == user_id
            )).where(Video.publish_date <= func.now())
        elif category == 'unread':
            base_count_query = base_count_query.outerjoin(VideoHistory, and_(
                VideoHistory.video_id == Video.id,
                VideoHistory.user_id == user_id
            )).where(
                and_(
                    VideoHistory.video_id.is_(None),
                    Video.publish_date <= func.now()
                )
            )
        elif category == 'preview':
            base_count_query = base_count_query.where(Video.publish_date > func.now())
        elif category == 'liked':
            base_count_query = base_count_query.join(VideoInteraction, and_(
                VideoInteraction.video_id == Video.id,
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 1
            )).where(Video.publish_date <= func.now())
        elif category == 'later':
            base_count_query = base_count_query.join(VideoInteraction, and_(
                VideoInteraction.video_id == Video.id,
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 3
            )).where(Video.publish_date <= func.now())
        else:  # 'all' category
            base_count_query = base_count_query.where(Video.publish_date <= func.now())

        # 添加通用过滤条件
        if subscription_id:
            base_count_query = base_count_query.where(SubscriptionVideo.subscription_id == subscription_id)
        if query:
            base_count_query = base_count_query.where(Video.title.like(f'%{query}%'))
        if domains:
            like_clauses = [Video.url.like(f"%{d}%") for d in domains if d]
            if like_clauses:
                base_count_query = base_count_query.where(or_(*like_clauses))
        # NSFW 过滤（方案A）
        if nsfw == 'yes':
            base_count_query = base_count_query.where(UserSubscription.is_nsfw == True)
        elif nsfw == 'no':
            base_count_query = base_count_query.where(UserSubscription.is_nsfw == False)
        else:
            if not show_nsfw:
                base_count_query = base_count_query.where(UserSubscription.is_nsfw == False)

        return session.execute(base_count_query).scalar() or 0


def _get_video_counts_in_session(session, user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                                 query: Optional[str] = None, nsfw: str = 'all', domains: Optional[List[str]] = None):
    """获取各类别视频数量 - 优化版：并行查询减少总耗时"""

    # 构建基础过滤条件（复用逻辑）
    def build_base_conditions():
        conditions = [
            Video.is_deleted == False,
            UserSubscription.is_deleted == False,
            Subscription.is_deleted == False,
            UserSubscription.user_id == user_id
        ]
        if subscription_id:
            conditions.append(SubscriptionVideo.subscription_id == subscription_id)
        if query:
            conditions.append(Video.title.like(f'%{query}%'))
        if domains:
            like_clauses = [Video.url.like(f"%{d}%") for d in domains if d]
            if like_clauses:
                conditions.append(or_(*like_clauses))
        if nsfw == 'yes':
            conditions.append(UserSubscription.is_nsfw == True)
        elif nsfw == 'no':
            conditions.append(UserSubscription.is_nsfw == False)
        else:
            if not show_nsfw:
                conditions.append(UserSubscription.is_nsfw == False)
        return and_(*conditions)

    base_conditions = build_base_conditions()

    # 1. 总数和预览数统计（按唯一 Video.id 计数）
    total_preview_query = (
        select(
            func.count(func.distinct(Video.id)).label('total'),
            func.count(func.distinct(Video.id)).filter(Video.publish_date > func.now()).label('preview')
        )
        .select_from(Video)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        .where(base_conditions)
    )
    total_result = session.execute(total_preview_query).first()
    total_count = total_result.total or 0
    preview_count = total_result.preview or 0
    all_count = total_count - preview_count

    # 2. 已读数统计（按唯一 Video.id 计数）
    read_count_query = (
        select(func.count(func.distinct(Video.id)))
        .select_from(VideoHistory)
        .join(Video, VideoHistory.video_id == Video.id)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            and_(
                base_conditions,
                VideoHistory.user_id == user_id,
                Video.publish_date <= func.now()
            )
        )
    )
    read_count = session.execute(read_count_query).scalar() or 0

    # 4. 点赞数统计（按唯一 Video.id 计数）
    like_count_query = (
        select(func.count(func.distinct(Video.id)))
        .select_from(VideoInteraction)
        .join(Video, VideoInteraction.video_id == Video.id)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            and_(
                base_conditions,
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 1,
                Video.publish_date <= func.now()
            )
        )
    )
    like_count = session.execute(like_count_query).scalar() or 0

    # 5. 稍后观看数统计（按唯一 Video.id 计数）
    later_count_query = (
        select(func.count(func.distinct(Video.id)))
        .select_from(VideoInteraction)
        .join(Video, VideoInteraction.video_id == Video.id)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            and_(
                base_conditions,
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 3,
                Video.publish_date <= func.now()
            )
        )
    )
    later_count = session.execute(later_count_query).scalar() or 0

    # 3. 未读数 = all - read（计算得出）
    unread_count = all_count - read_count


    return {
        "all": all_count,
        "read": read_count,
        "unread": unread_count,
        "preview": preview_count,
        "liked": like_count,
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
        # 第一步：基于 _build_base_video_query 和类别过滤，按唯一 video.id 做分页
        base_query = _build_base_video_query(user_id, show_nsfw, subscription_id, query, nsfw, domains)

        # 按类别追加条件（与各 _query_* 保持一致）
        if category == 'read':
            base_query = base_query.join(VideoHistory, and_(
                VideoHistory.video_id == Video.id,
                VideoHistory.user_id == user_id
            )).where(Video.publish_date <= func.now())
        elif category == 'unread':
            base_query = base_query.outerjoin(VideoHistory, and_(
                VideoHistory.video_id == Video.id,
                VideoHistory.user_id == user_id
            )).where(
                and_(
                    VideoHistory.video_id.is_(None),
                    Video.publish_date <= func.now()
                )
            )
        elif category == 'preview':
            base_query = base_query.where(Video.publish_date > func.now())
        elif category == 'liked':
            base_query = base_query.join(VideoInteraction, and_(
                VideoInteraction.video_id == Video.id,
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 1
            )).where(Video.publish_date <= func.now())
        elif category == 'later':
            base_query = base_query.join(VideoInteraction, and_(
                VideoInteraction.video_id == Video.id,
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 3
            )).where(Video.publish_date <= func.now())
        else:  # 'all'
            base_query = base_query.where(Video.publish_date <= func.now())

        # 排序字段与原逻辑保持一致
        if sort_by == 'created_at':
            order_column = Video.created_at.desc()
        else:
            order_column = Video.publish_date.desc()

        # 只选择唯一的 Video.id 进行分页
        # 注意：PostgreSQL 要求 DISTINCT + ORDER BY 的列必须都出现在 SELECT 列表中
        id_query = (
            base_query
            .with_only_columns(Video.id, order_column)
            .distinct()
            .order_by(order_column)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        id_rows = session.execute(id_query).all()
        # 只使用第 0 列的 video.id 作为分页结果
        video_ids = [row[0] for row in id_rows]

        if not video_ids:
            # 即使当前页没有数据，也要返回正确的 total
            total_count = _get_category_count(
                user_id, show_nsfw, category, subscription_id, query, nsfw, domains
            ) if with_total else None
            return [], total_count

        # 第二步：根据本页 video_ids 查询详细信息（视频 + 所有关联订阅）
        detail_rows = session.execute(
            select(Video, SubscriptionVideo.subscription_id.label('subscription_id'))
            .select_from(Video)
            .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
            .where(Video.id.in_(video_ids))
        ).all()

        # 聚合：同一个 video.id 只保留一个 Video 对象，并收集所有 subscription_id
        video_map: Dict[int, VideoDto] = {}
        video_subscriptions_map: Dict[int, set] = {}
        for row in detail_rows:
            video = row[0]
            subscription_id_val = row[1]

            if video.id not in video_map:
                video_dto = VideoDto.model_validate({
                    **video.to_dict(),
                    'subscription_id': subscription_id_val
                })
                video_map[video.id] = video_dto

            if video.id not in video_subscriptions_map:
                video_subscriptions_map[video.id] = set()
            if subscription_id_val is not None:
                video_subscriptions_map[video.id].add(subscription_id_val)

        # 只计算当前类别的总数（用于分页），已改为按唯一 Video.id 计数
        total_count = _get_category_count(
            user_id, show_nsfw, category, subscription_id, query, nsfw, domains
        ) if with_total else None

        # 获取所有关联订阅信息（包含 is_nsfw）
        subscription_ids = list({sid for sids in video_subscriptions_map.values() for sid in sids}) if video_subscriptions_map else []
        subscription_results = session.execute(
            select(Subscription, UserSubscription.is_nsfw)
            .join(UserSubscription, Subscription.id == UserSubscription.subscription_id)
            .where(
                and_(
                    Subscription.id.in_(subscription_ids),
                    UserSubscription.user_id == user_id
                )
            )
        ).all() if subscription_ids else []

        # 构建订阅字典，包含 is_nsfw
        subscriptions_dict = {sub.id: {'subscription': sub, 'is_nsfw': is_nsfw}
                              for sub, is_nsfw in subscription_results}

        # 为了保持顺序，按分页得到的 video_ids 顺序输出
        ordered_videos = [video_map[vid] for vid in video_ids if vid in video_map]

        # 获取视频相关创作者
        creators = session.execute(
            select(Creator, VideoCreator)
            .join(VideoCreator, Creator.id == VideoCreator.creator_id)
            .where(VideoCreator.video_id.in_(video_ids))
        ).all() if video_ids else []

        creators_dict: Dict[int, List[Creator]] = {}
        for creator, video_creator in creators:
            if video_creator.video_id not in creators_dict:
                creators_dict[video_creator.video_id] = []
            creators_dict[video_creator.video_id].append(creator)

        # 获取视频历史记录
        if video_ids:
            video_history = session.execute(
                select(VideoHistory)
                .where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id.in_(video_ids)
                    )
                )
            ).scalars().all()
        else:
            video_history = []
        video_history_dict = {vh.video_id: vh for vh in video_history}

        # 构建返回数据：同一个视频只返回一次，并包含所有关联订阅
        video_list = []
        for video in ordered_videos:
            related_subscription_ids = video_subscriptions_map.get(video.id, set())
            subscriptions_list = []
            for sid in related_subscription_ids:
                subscription_data = subscriptions_dict.get(sid)
                if not subscription_data:
                    continue
                subscription_info = subscription_data['subscription']
                is_nsfw = subscription_data['is_nsfw']
                subscriptions_list.append({
                    'id': subscription_info.id,
                    'name': subscription_info.name,
                    'url': subscription_info.url,
                    'type': subscription_info.type,
                    'avatar': subscription_info.avatar,
                    'is_nsfw': is_nsfw
                })

            video_data = {
                'id': video.id,
                'title': video.title,
                'url': video.url,
                'thumbnail': thumbnail_downloader_service.get_thumbnail_url(video.id, video.thumbnail, video.url),
                'duration': video.duration,
                'last_position': video_history_dict[video.id].last_position if video.id in video_history_dict else 0,
                'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
                'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'subscriptions': subscriptions_list,
                'actors': [creator.to_dict() for creator in creators_dict.get(video.id, [])]
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
    download_service.start(params)


def get_video(user_id, video_id):
    with get_session() as session:
        video = session.scalars(select(Video).where(Video.id == video_id)).first()
        if not video:
            return None

        subscription_videos = session.scalars(
            select(SubscriptionVideo).where(SubscriptionVideo.video_id == video_id)
        ).all()
        subscription_ids = [sv.subscription_id for sv in subscription_videos] or []

        # 获取订阅信息（包含 is_nsfw）
        subscription_results = session.execute(
            select(Subscription, UserSubscription.is_nsfw)
            .join(UserSubscription, Subscription.id == UserSubscription.subscription_id)
            .where(
                and_(
                    Subscription.id.in_(subscription_ids),
                    UserSubscription.user_id == user_id
                )
            )
        ).all() if subscription_ids else []

        # 计算每个订阅的已解析视频数（total_extract）
        counts_map = {}
        if subscription_ids:
            rows = session.execute(
                select(SubscriptionVideo.subscription_id, func.count(SubscriptionVideo.video_id).label('video_count'))
                .where(SubscriptionVideo.subscription_id.in_(subscription_ids))
                .group_by(SubscriptionVideo.subscription_id)
            ).all()
            counts_map = {row[0]: row[1] for row in rows}

        # 构造包含 total_extract 和 is_nsfw 的订阅信息
        subscriptions_data = []
        for subscription, is_nsfw in subscription_results:
            s_dict = subscription.to_dict()
            s_dict['total_extract'] = counts_map.get(subscription.id, 0)
            s_dict['is_nsfw'] = is_nsfw
            subscriptions_data.append(s_dict)

        creators = session.scalars(
            select(Creator, VideoCreator)
            .join(VideoCreator, Creator.id == VideoCreator.creator_id)
            .where(VideoCreator.video_id == video_id)
        ).all()

        # 优化：直接在当前 session 查询，避免创建新 session
        video_history = session.execute(
            select(VideoHistory)
            .where(
                and_(
                    VideoHistory.user_id == user_id,
                    VideoHistory.video_id == video_id
                )
            )
        ).scalar_one_or_none()

        video_interaction = session.execute(
            select(VideoInteraction)
            .where(
                and_(
                    VideoInteraction.user_id == user_id,
                    VideoInteraction.video_id == video_id
                )
            )
        ).scalar_one_or_none()

        video_data = {
            **video.to_dict(),
            'thumbnail': thumbnail_downloader_service.get_thumbnail_url(video.id, video.thumbnail, video.url),
            'interaction_type': video_interaction.interaction_type if video_interaction else None,
            'last_position': video_history.last_position if video_history else 0,
            'domain': url_helper.extract_top_level_domain(video.url),
            'subscriptions': subscriptions_data,
            'creators': [creator.to_dict() for creator in creators]
        }

        return video_data
