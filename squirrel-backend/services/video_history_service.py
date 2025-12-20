from typing import List
from sqlalchemy import func
from core.database import get_session
from models.video_history import VideoHistory
from models.video import Video
from models.subscription import Subscription
from models.links import SubscriptionVideo, UserSubscription
from schemas.video_history import HistoryCreate
from utils.url_helper import get_site_from_url


def update_history(user_id: int, data: HistoryCreate):
    """
    更新观看记录（合并式更新）
    """
    with get_session() as session:
        # 查找最近24小时内的记录
        history = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id,
            VideoHistory.video_id == data.video_id
        ).first()

        if history:
            history.watch_duration += 0
            history.last_position = data.last_position
            history.end_time = func.now()
        else:
            history = VideoHistory(
                user_id=user_id,
                video_id=data.video_id,
                start_time=func.now(),
                end_time=func.now(),
                duration=0,
                watch_duration=0,
                last_position=data.last_position
            )
            session.add(history)

        session.commit()


def list_histories(user_id: int, filters: dict, page: int, page_size: int) -> dict:
    """
    返回包含视频详情的历史记录列表，字段适配前端视频卡片：
    - id, title, url, thumbnail, duration, uploaded_at, created_at
    - subscriptions: [{ id, name, url, type, avatar }]
    - last_position
    """
    with get_session() as session:
        # 基础历史记录查询（先取 video_id 和 last_position + 排序/分页）
        base_query = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id
        )

        if filters.get('video_id'):
            base_query = base_query.filter(VideoHistory.video_id == filters['video_id'])
        if filters.get('min_duration'):
            base_query = base_query.filter(VideoHistory.duration >= filters['min_duration'])
        if filters.get('start_date'):
            base_query = base_query.filter(VideoHistory.created_at >= filters['start_date'])
        if filters.get('end_date'):
            base_query = base_query.filter(VideoHistory.created_at <= filters['end_date'])

        total = base_query.count()

        histories = base_query.order_by(VideoHistory.end_time.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        if not histories:
            return {
                "items": [],
                "total": total,
                "page": page,
                "page_size": page_size
            }

        # 收集 video_id 集合
        video_ids = [h.video_id for h in histories]

        # 批量查视频详情
        videos = session.query(Video).filter(Video.id.in_(video_ids)).all()
        video_map = {v.id: v for v in videos}

        # 查订阅关系并汇总对应订阅信息
        subs_links = session.query(SubscriptionVideo).filter(SubscriptionVideo.video_id.in_(video_ids)).all()
        sub_ids = list(set(link.subscription_id for link in subs_links))
        subs = session.query(Subscription).filter(Subscription.id.in_(sub_ids)).all()
        sub_map = {s.id: s for s in subs}
        
        # 查询用户订阅关系以获取 is_nsfw 标记
        user_subs = session.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.subscription_id.in_(sub_ids)
        ).all()
        user_sub_nsfw_map = {us.subscription_id: us.is_nsfw for us in user_subs}
        
        # 为每个 video_id 组织订阅列表（多数情况下一个）
        video_subs = {}
        for link in subs_links:
            video_subs.setdefault(link.video_id, []).append(sub_map.get(link.subscription_id))

        # 组装返回
        items = []
        for h in histories:
            v = video_map.get(h.video_id)
            if not v:
                # 若视频已被删除或未找到，跳过
                continue
            subs_for_video = [
                {
                    'id': s.id,
                    'name': s.name,
                    'url': s.url,
                    'type': s.type,
                    'avatar': s.avatar,
                    'is_nsfw': user_sub_nsfw_map.get(s.id, False)
                }
                for s in (video_subs.get(v.id) or []) if s is not None
            ]
            
            # 提取站点信息（用于筛选和返回）
            video_site = get_site_from_url(v.url)
            if not video_site and subs_for_video:
                for sub_info in subs_for_video:
                    sub_url = sub_info.get('url')
                    if sub_url:
                        video_site = get_site_from_url(sub_url)
                        if video_site:
                            break
            
            # 应用筛选条件
            # NSFW 筛选
            if filters.get('nsfw') and filters['nsfw'] != 'all':
                nsfw_filter = filters['nsfw']
                is_nsfw = any(s.get('is_nsfw') for s in subs_for_video)
                # 前端发送 'yes'/'no'，后端也支持 'true'/'false'
                if nsfw_filter in ('yes', 'true') and not is_nsfw:
                    continue
                if nsfw_filter in ('no', 'false') and is_nsfw:
                    continue
            
            # 站点筛选
            if filters.get('site'):
                site_filter = filters['site']
                if video_site != site_filter:
                    continue
            
            item = {
                'id': v.id,
                'title': v.title,
                'url': v.url,
                'thumbnail': f'/api/video/thumbnail/{v.id}',
                'duration': v.duration,
                'last_position': h.last_position or 0,
                'uploaded_at': v.publish_date.strftime('%Y-%m-%d %H:%M:%S') if v.publish_date else None,
                'created_at': v.created_at.strftime('%Y-%m-%d %H:%M:%S') if v.created_at else None,
                'subscriptions': subs_for_video,
                'site': video_site,
            }
            items.append(item)

        return {
            "items": items,
            "total": len(items),
            "page": page,
            "page_size": page_size
        }


def get_videos_by_ids(user_id: int, video_ids: List[int]) -> List[VideoHistory]:
    with get_session() as session:
        videos = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id,
            VideoHistory.video_id.in_(video_ids)
        ).all()
        return videos


def get_video_history(user_id: int, video_id: int) -> VideoHistory:
    with get_session() as session:
        video_history = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id,
            VideoHistory.video_id == video_id
        ).first()
        return video_history


def clear_histories(user_id: int, video_ids: List[int] = None):
    """
    清除观看历史（支持批量）
    """
    with get_session() as session:
        query = session.query(VideoHistory).filter(
            VideoHistory.user_id == user_id
        )

        if video_ids:
            query = query.filter(VideoHistory.video_id.in_(video_ids))

        delete_count = query.delete()
        session.commit()
        return delete_count
