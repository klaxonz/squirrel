from datetime import datetime
from typing import List, Tuple, Optional

from sqlalchemy import select, func, and_, or_

from core.database import get_session
from schemas.video.dto.video_dto import VideoExtractDto, VideoDto, VideoUrlDto
from sites.handler import VideoUrlHandlerFactory
from models.creator import Creator
from models.links import VideoCreator, SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from services import download_service, subscription_video_service, user_config_service, video_history_service, \
    video_interaction_service
from utils import url_helper
from utils.url_helper import extract_top_level_domain


def get_video_by_url(url: str) -> Video:
    with get_session() as session:
        video = session.scalars(select(Video).where(Video.url == url)).first()
        return video


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


def get_video_url(video_id: int) -> VideoUrlDto:
    video_domain = None
    with get_session() as session:
        video = session.get(Video, video_id)
        if not video:
            raise ValueError(f"Video with ID {video_id} not found")

        video_domain = extract_top_level_domain(video.url)

    if video_domain is None:
        raise ValueError(f"Invalid video URL: {video.url}")

    handler = VideoUrlHandlerFactory.get_handler(video_domain)
    return handler.get_video_url(video)


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
                     sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all', domains: Optional[List[str]] = None):
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
                      sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all', domains: Optional[List[str]] = None):
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
                        sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all', domains: Optional[List[str]] = None):
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
                         sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all', domains: Optional[List[str]] = None):
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
                       sort_by: str = 'publish_date', page: int = 1, page_size: int = 20, nsfw: str = 'all', domains: Optional[List[str]] = None):
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


def _get_category_count(user_id: int, show_nsfw: bool, category: str, subscription_id: Optional[int] = None,
                       query: Optional[str] = None, nsfw: str = 'all', domains: Optional[List[str]] = None) -> int:
    """获取特定类别的视频数量，优化的count查询"""
    with get_session() as session:
        # 基础count查询，只选择Video.id用于计数
        base_count_query = (
            select(func.count(Video.id))
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


def _get_video_counts(user_id: int, show_nsfw: bool, subscription_id: Optional[int] = None,
                     query: Optional[str] = None, nsfw: str = 'all', domains: Optional[List[str]] = None):
    """获取各类别视频数量"""
    with get_session() as session:
        # 基础计数查询
        base_count_query = (
            select(Video.id)
            .select_from(Video)
            .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
            .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
            .join(Subscription, UserSubscription.subscription_id == Subscription.id)
            .outerjoin(VideoHistory, and_(
                VideoHistory.video_id == Video.id,
                VideoHistory.user_id == user_id
            ))
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
            base_count_query = base_count_query.where(SubscriptionVideo.subscription_id == subscription_id)
        if query:
            base_count_query = base_count_query.where(Video.title.like(f"%{query}%"))
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

        # 各类别计数
        all_count = session.execute(
            select(func.count()).select_from(
                base_count_query.where(Video.publish_date <= func.now()).subquery()
            )
        ).scalar() or 0

        preview_count = session.execute(
            select(func.count()).select_from(
                base_count_query.where(Video.publish_date > func.now()).subquery()
            )
        ).scalar() or 0

        read_count = session.execute(
            select(func.count()).select_from(
                base_count_query.where(
                    and_(
                        VideoHistory.video_id.is_not(None),
                        Video.publish_date <= func.now()
                    )
                ).subquery()
            )
        ).scalar() or 0

        unread_count = session.execute(
            select(func.count()).select_from(
                base_count_query.where(
                    and_(
                        VideoHistory.video_id.is_(None),
                        Video.publish_date <= func.now()
                    )
                ).subquery()
            )
        ).scalar() or 0

        # 点赞视频计数
        like_count_query = (
            select(func.count())
            .select_from(Video)
            .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
            .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
            .join(Subscription, UserSubscription.subscription_id == Subscription.id)
            .join(VideoInteraction, and_(
                VideoInteraction.video_id == Video.id,
                VideoInteraction.user_id == user_id,
                VideoInteraction.interaction_type == 1
            ))
            .where(
                and_(
                    Video.is_deleted == False,
                    UserSubscription.is_deleted == False,
                    Subscription.is_deleted == False,
                    UserSubscription.user_id == user_id,
                    Video.publish_date <= func.now()
                )
            )
        )

        if subscription_id:
            like_count_query = like_count_query.where(SubscriptionVideo.subscription_id == subscription_id)
        if query:
            like_count_query = like_count_query.where(Video.title.like(f"%{query}%"))
        if domains:
            like_clauses = [Video.url.like(f"%{d}%") for d in domains if d]
            if like_clauses:
                like_count_query = like_count_query.where(or_(*like_clauses))
        # NSFW 过滤（方案A）
        if nsfw == 'yes':
            like_count_query = like_count_query.where(UserSubscription.is_nsfw == True)
        elif nsfw == 'no':
            like_count_query = like_count_query.where(UserSubscription.is_nsfw == False)
        else:
            if not show_nsfw:
                like_count_query = like_count_query.where(UserSubscription.is_nsfw == False)

        like_video_count = session.execute(like_count_query).scalar() or 0

        return {
            "all": all_count,
            "read": read_count,
            "unread": unread_count,
            "preview": preview_count,
            "liked": like_video_count
        }


def list_videos(
        user_id: int,
        query: str,
        subscription_id: int,
        category: str,
        sort_by: str,
        nsfw: str,
        domains: Optional[List[str]],
        page: int,
        page_size: int
) -> Tuple[List[dict], int, dict]:
    user_config = user_config_service.get_config(user_id)
    show_nsfw = user_config.get('showNsfw', False)

    # 根据类别选择查询方法
    query_methods = {
        'all': _query_all_videos,
        'read': _query_read_videos,
        'unread': _query_unread_videos,
        'preview': _query_preview_videos,
        'liked': _query_liked_videos
    }

    query_method = query_methods.get(category, _query_all_videos)

    with get_session() as session:
        # 执行主查询
        main_query = query_method(user_id, show_nsfw, subscription_id, query, sort_by, page, page_size, nsfw=nsfw, domains=domains)
        results = session.execute(main_query).all()

        videos = []
        for row in results:
            video = row[0]  # Video object
            subscription_id_val = row[1]  # subscription_id
            video_dto = VideoDto.model_validate({
                **video.to_dict(),
                'subscription_id': subscription_id_val
            })
            videos.append(video_dto)

        # 获取总数（当前类别）- 使用优化的count查询
        total_count = _get_category_count(user_id, show_nsfw, category, subscription_id, query, nsfw=nsfw, domains=domains)

        # 获取各类别计数
        counts = _get_video_counts(user_id, show_nsfw, subscription_id, query, nsfw=nsfw, domains=domains)

        # 获取订阅信息
        subscription_ids = list(set(video.subscription_id for video in videos))
        subscriptions = session.query(Subscription).filter(Subscription.id.in_(subscription_ids)).all()

        # 获取视频相关创作者
        video_ids = [video.id for video in videos]
        creators = session.execute(select(Creator, VideoCreator)
                                   .join(VideoCreator, Creator.id == VideoCreator.creator_id)
                                   .where(VideoCreator.video_id.in_(video_ids))).all()

        creators_dict = {}
        for creator, video_creator in creators:
            if video_creator.video_id not in creators_dict:
                creators_dict[video_creator.video_id] = []
            creators_dict[video_creator.video_id].append(creator)

        # 获取视频历史记录
        video_history = video_history_service.get_videos_by_ids(user_id, video_ids)
        video_history_dict = {vh.video_id: vh for vh in video_history}

        # 构建返回数据
        video_list = []
        for video in videos:
            subscription_info = next((sub for sub in subscriptions if sub.id == video.subscription_id), None)
            video_data = {
                'id': video.id,
                'title': video.title,
                'url': video.url,
                'thumbnail': video.thumbnail,
                'duration': video.duration,
                'last_position': video_history_dict[video.id].last_position if video.id in video_history_dict else 0,
                'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
                'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'subscriptions': [
                    {
                        'id': subscription_info.id,
                        'name': subscription_info.name,
                        'url': subscription_info.url,
                        'type': subscription_info.type,
                        "avatar": subscription_info.avatar
                    }
                ] if subscription_info else [],
                'actors': [creator.to_dict() for creator in creators_dict.get(video.id, [])]
            }
            video_list.append(video_data)

        return video_list, total_count, counts


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

        subscriptions = session.scalars(
            select(Subscription).where(Subscription.id.in_(subscription_ids))
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

        # 构造包含 total_extract 的订阅信息
        subscriptions_data = []
        for subscription in subscriptions:
            s_dict = subscription.to_dict()
            s_dict['total_extract'] = counts_map.get(subscription.id, 0)
            subscriptions_data.append(s_dict)

        creators = session.scalars(
            select(Creator, VideoCreator)
            .join(VideoCreator, Creator.id == VideoCreator.creator_id)
            .where(VideoCreator.video_id == video_id)
        ).all()

        video_history = video_history_service.get_video_history(user_id, video_id)
        video_interaction = video_interaction_service.get_video_interaction(user_id, video_id)

        video_data = {
            **video.to_dict(),
            'interaction_type': video_interaction.interaction_type if video_interaction else None,
            'last_position': video_history.last_position if video_history else 0,
            'domain': url_helper.extract_top_level_domain(video.url),
            'subscriptions': subscriptions_data,
            'creators': [creator.to_dict() for creator in creators]
        }

        return video_data

