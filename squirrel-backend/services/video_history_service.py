from typing import List

from sqlalchemy import select, func, delete

from core.database import get_session
from models.video_history import VideoHistory
from models.video import Video
from models.subscription import Subscription
from models.links import SubscriptionVideo, UserSubscription
from schemas.video_history import HistoryCreate
from utils.url_helper import get_site_from_url
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service


def update_history(user_id: int, data: HistoryCreate):
    with get_session() as session:
        history = session.scalars(
            select(VideoHistory).where(
                VideoHistory.user_id == user_id,
                VideoHistory.video_id == data.video_id
            )
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
    with get_session() as session:
        conditions = [VideoHistory.user_id == user_id]

        if filters.get('video_id'):
            conditions.append(VideoHistory.video_id == filters['video_id'])
        if filters.get('min_duration'):
            conditions.append(VideoHistory.duration >= filters['min_duration'])
        if filters.get('start_date'):
            conditions.append(VideoHistory.created_at >= filters['start_date'])
        if filters.get('end_date'):
            conditions.append(VideoHistory.created_at <= filters['end_date'])

        total = session.scalar(
            select(func.count(VideoHistory.id)).where(*conditions)
        )

        histories = session.scalars(
            select(VideoHistory)
            .where(*conditions)
            .order_by(VideoHistory.end_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        if not histories:
            return {
                "items": [],
                "total": total,
                "page": page,
                "page_size": page_size
            }

        video_ids = [h.video_id for h in histories]

        videos = session.scalars(
            select(Video).where(Video.id.in_(video_ids))
        ).all()
        video_map = {v.id: v for v in videos}

        subs_links = session.scalars(
            select(SubscriptionVideo).where(SubscriptionVideo.video_id.in_(video_ids))
        ).all()
        sub_ids = list(set(link.subscription_id for link in subs_links))

        subs = session.scalars(
            select(Subscription).where(Subscription.id.in_(sub_ids))
        ).all()
        sub_map = {s.id: s for s in subs}

        user_subs = session.scalars(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.subscription_id.in_(sub_ids)
            )
        ).all()
        user_sub_nsfw_map = {us.subscription_id: us.is_nsfw for us in user_subs}

        video_subs = {}
        for link in subs_links:
            video_subs.setdefault(link.video_id, []).append(sub_map.get(link.subscription_id))

        items = []
        for h in histories:
            v = video_map.get(h.video_id)
            if not v:
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

            video_site = get_site_from_url(v.url)
            if not video_site and subs_for_video:
                for sub_info in subs_for_video:
                    sub_url = sub_info.get('url')
                    if sub_url:
                        video_site = get_site_from_url(sub_url)
                        if video_site:
                            break

            if filters.get('nsfw') and filters['nsfw'] != 'all':
                nsfw_filter = filters['nsfw']
                is_nsfw = any(s.get('is_nsfw') for s in subs_for_video)
                if nsfw_filter in ('yes', 'true') and not is_nsfw:
                    continue
                if nsfw_filter in ('no', 'false') and is_nsfw:
                    continue

            if filters.get('site'):
                site_filter = filters['site']
                if video_site != site_filter:
                    continue

            item = {
                'id': v.id,
                'title': v.title,
                'url': v.url,
                'thumbnail': thumbnail_downloader_service.get_thumbnail_url(v.id, v.thumbnail, v.url),
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
        videos = session.scalars(
            select(VideoHistory).where(
                VideoHistory.user_id == user_id,
                VideoHistory.video_id.in_(video_ids)
            )
        ).all()
        return videos


def get_video_history(user_id: int, video_id: int) -> VideoHistory:
    with get_session() as session:
        video_history = session.scalars(
            select(VideoHistory).where(
                VideoHistory.user_id == user_id,
                VideoHistory.video_id == video_id
            )
        ).first()
        return video_history


def clear_histories(user_id: int, video_ids: List[int] = None):
    with get_session() as session:
        conditions = [VideoHistory.user_id == user_id]

        if video_ids:
            conditions.append(VideoHistory.video_id.in_(video_ids))

        result = session.execute(
            delete(VideoHistory).where(*conditions)
        )
        session.commit()
        return result.rowcount
