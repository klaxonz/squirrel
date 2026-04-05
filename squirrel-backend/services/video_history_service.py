from typing import Iterable, List

from sqlalchemy import and_, delete, exists, func, or_, select

from core.database import get_session
from models.video_history import VideoHistory
from models.video import Video
from models.subscription import Subscription
from models.links import SubscriptionVideo, UserSubscription
from schemas.video_history import HistoryCreate
from utils import url_helper
from utils.site_catalog import SiteCatalog
from utils.url_helper import get_site_from_url
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service


def _normalize_history_reports(reports: Iterable[HistoryCreate]) -> list[HistoryCreate]:
    latest_by_video_id: dict[int, HistoryCreate] = {}
    for report in reports:
        latest_by_video_id[report.video_id] = report
    return list(latest_by_video_id.values())


def _apply_history_updates(session, user_id: int, reports: list[HistoryCreate]) -> None:
    normalized_reports = _normalize_history_reports(reports)
    if not normalized_reports:
        return

    video_ids = [report.video_id for report in normalized_reports]
    existing_histories = session.scalars(
        select(VideoHistory).where(
            VideoHistory.user_id == user_id,
            VideoHistory.video_id.in_(video_ids)
        )
        .order_by(VideoHistory.video_id.asc(), VideoHistory.end_time.desc(), VideoHistory.id.desc())
    ).all()

    histories_by_video_id: dict[int, list[VideoHistory]] = {}
    for history in existing_histories:
        histories_by_video_id.setdefault(history.video_id, []).append(history)

    for report in normalized_reports:
        histories = histories_by_video_id.get(report.video_id, [])

        if histories:
            history = histories[0]
            history.watch_duration += 0
            history.last_position = report.last_position
            history.end_time = func.now()
            duplicate_ids = [item.id for item in histories[1:]]
            if duplicate_ids:
                session.execute(
                    delete(VideoHistory).where(VideoHistory.id.in_(duplicate_ids))
                )
            continue

        session.add(
            VideoHistory(
                user_id=user_id,
                video_id=report.video_id,
                start_time=func.now(),
                end_time=func.now(),
                duration=0,
                watch_duration=0,
                last_position=report.last_position
            )
        )


def update_history(user_id: int, data: HistoryCreate):
    with get_session() as session:
        _apply_history_updates(session, user_id, [data])
        session.commit()


def batch_update_histories(user_id: int, reports: list[HistoryCreate]) -> None:
    with get_session() as session:
        _apply_history_updates(session, user_id, reports)
        session.commit()


def list_histories(user_id: int, filters: dict, page: int, page_size: int) -> dict:
    with get_session() as session:
        conditions = [
            VideoHistory.user_id == user_id,
            exists(
                select(1)
                .select_from(Video)
                .where(Video.id == VideoHistory.video_id)
            )
        ]

        if filters.get('query'):
            search_term = filters['query'].strip()
            if search_term:
                search_pattern = f'%{search_term}%'
                title_match = exists(
                    select(1)
                    .select_from(Video)
                    .where(
                        and_(
                            Video.id == VideoHistory.video_id,
                            Video.title.ilike(search_pattern)
                        )
                    )
                )
                subscription_match = exists(
                    select(1)
                    .select_from(SubscriptionVideo)
                    .join(
                        Subscription,
                        Subscription.id == SubscriptionVideo.subscription_id
                    )
                    .join(
                        UserSubscription,
                        UserSubscription.subscription_id == Subscription.id
                    )
                    .where(
                        SubscriptionVideo.video_id == VideoHistory.video_id,
                        UserSubscription.user_id == user_id,
                        UserSubscription.is_deleted == False,
                        Subscription.is_deleted == False,
                        Subscription.name.ilike(search_pattern)
                    )
                )
                conditions.append(or_(title_match, subscription_match))

        if filters.get('video_id'):
            conditions.append(VideoHistory.video_id == filters['video_id'])
        if filters.get('min_duration'):
            conditions.append(VideoHistory.duration >= filters['min_duration'])
        if filters.get('start_date'):
            conditions.append(VideoHistory.created_at >= filters['start_date'])
        if filters.get('end_date'):
            conditions.append(VideoHistory.created_at <= filters['end_date'])
        if filters.get('nsfw') and filters['nsfw'] != 'all':
            nsfw_history_exists = exists(
                select(1)
                .select_from(SubscriptionVideo)
                .join(
                    UserSubscription,
                    UserSubscription.subscription_id == SubscriptionVideo.subscription_id
                )
                .where(
                    SubscriptionVideo.video_id == VideoHistory.video_id,
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_nsfw == True
                )
            )
            nsfw_filter = filters['nsfw']
            if nsfw_filter in ('yes', 'true'):
                conditions.append(nsfw_history_exists)
            elif nsfw_filter in ('no', 'false'):
                conditions.append(~nsfw_history_exists)
        if filters.get('site'):
            resolved_domains = SiteCatalog.resolve_domains(filters['site'])
            normalized_domains = [
                domain
                for domain in {
                    url_helper.normalize_domain(raw_domain)
                    for raw_domain in resolved_domains
                    if raw_domain
                }
                if domain
            ]
            if not normalized_domains:
                return {
                    'items': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size
                }
            conditions.append(
                exists(
                    select(1)
                    .select_from(Video)
                    .where(
                        and_(
                            Video.id == VideoHistory.video_id,
                            Video.domain.in_(normalized_domains)
                        )
                    )
                )
            )

        ranked_histories = (
            select(
                VideoHistory.id.label('id'),
                VideoHistory.end_time.label('end_time'),
                func.row_number().over(
                    partition_by=VideoHistory.video_id,
                    order_by=(VideoHistory.end_time.desc(), VideoHistory.id.desc())
                ).label('row_num')
            )
            .where(*conditions)
            .subquery()
        )

        latest_history_ids = (
            select(
                ranked_histories.c.id,
                ranked_histories.c.end_time
            )
            .where(ranked_histories.c.row_num == 1)
            .subquery()
        )

        total = session.scalar(
            select(func.count()).select_from(latest_history_ids)
        )

        histories = session.scalars(
            select(VideoHistory)
            .join(latest_history_ids, latest_history_ids.c.id == VideoHistory.id)
            .order_by(latest_history_ids.c.end_time.desc(), VideoHistory.id.desc())
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

            item = {
                'id': v.id,
                'history_id': h.id,
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
            "total": total,
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


def delete_history(user_id: int, history_id: int) -> int:
    with get_session() as session:
        result = session.execute(
            delete(VideoHistory).where(
                VideoHistory.id == history_id,
                VideoHistory.user_id == user_id
            )
        )
        session.commit()
        return result.rowcount


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
