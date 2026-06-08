from collections.abc import Callable, Generator, Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, exists, false, func, select
from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service
from models.links import SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from schemas.video_history import HistoryCreate
from services import user_config_service
from services.nsfw_policy import resolve_effective_nsfw_filter
from services.video_list_service import _merge_profiles, _video_extra_profiles
from services.video_query import build_video_search_clauses
from utils import url_helper
from utils.site_catalog import SiteCatalog
from utils.url_helper import get_site_from_url

SessionFactory = Callable[[], Generator[Session, None, None]]


class VideoHistoryService:
    def __init__(self, session_factory: SessionFactory | None = None, get_user_config=None):
        self._session_factory = session_factory or _default_get_session
        self._get_user_config = get_user_config or user_config_service.get_config

    @staticmethod
    def _resolve_reported_at(report: HistoryCreate) -> datetime:
        raw_timestamp = report.timestamp
        if raw_timestamp is None:
            return datetime.now()

        seconds = raw_timestamp / 1000 if raw_timestamp > 1_000_000_000_000 else raw_timestamp
        return datetime.fromtimestamp(seconds)

    @staticmethod
    def _is_newer_report(
        candidate: HistoryCreate, current: HistoryCreate, *, candidate_index: int, current_index: int,
    ) -> bool:
        if candidate.timestamp is not None and current.timestamp is not None:
            candidate_reported_at = VideoHistoryService._resolve_reported_at(candidate)
            current_reported_at = VideoHistoryService._resolve_reported_at(current)
            if candidate_reported_at != current_reported_at:
                return candidate_reported_at > current_reported_at
            if candidate.last_position != current.last_position:
                return candidate.last_position >= current.last_position

        return candidate_index >= current_index

    @staticmethod
    def _normalize_history_reports(reports: Iterable[HistoryCreate]) -> list[HistoryCreate]:
        latest_by_video_id: dict[int, tuple[HistoryCreate, int]] = {}
        for index, report in enumerate(reports):
            current = latest_by_video_id.get(report.video_id)
            if current is None or VideoHistoryService._is_newer_report(
                report, current[0], candidate_index=index, current_index=current[1],
            ):
                latest_by_video_id[report.video_id] = (report, index)
        return [item[0] for item in latest_by_video_id.values()]

    def _apply_history_updates(self, session: Session, user_id: int, reports: list[HistoryCreate]) -> None:
        normalized_reports = self._normalize_history_reports(reports)
        if not normalized_reports:
            return

        video_ids = [report.video_id for report in normalized_reports]
        existing_histories = session.scalars(
            select(VideoHistory)
            .where(
                VideoHistory.user_id == user_id,
                VideoHistory.video_id.in_(video_ids),
            )
            .order_by(VideoHistory.video_id.asc(), VideoHistory.end_time.desc(), VideoHistory.id.desc()),
        ).all()

        histories_by_video_id: dict[int, list[VideoHistory]] = {}
        for history in existing_histories:
            histories_by_video_id.setdefault(history.video_id, []).append(history)

        for report in normalized_reports:
            histories = histories_by_video_id.get(report.video_id, [])
            reported_at = self._resolve_reported_at(report)

            if histories:
                history = histories[0]
                duplicate_ids = [item.id for item in histories[1:]]
                if duplicate_ids:
                    session.execute(
                        delete(VideoHistory).where(VideoHistory.id.in_(duplicate_ids)),
                    )

                existing_end_time = history.end_time or history.updated_at or history.created_at or reported_at
                if reported_at < existing_end_time and report.last_position <= history.last_position:
                    continue

                history.watch_duration += 0
                history.last_position = report.last_position
                history.end_time = max(reported_at, existing_end_time)
                continue

            session.add(
                VideoHistory(
                    user_id=user_id,
                    video_id=report.video_id,
                    start_time=reported_at,
                    end_time=reported_at,
                    duration=0,
                    watch_duration=0,
                    last_position=report.last_position,
                ),
            )

    def update_history(self, user_id: int, data: HistoryCreate):
        with self._session_factory() as session:
            self._apply_history_updates(session, user_id, [data])
            session.commit()

    def batch_update_histories(self, user_id: int, reports: list[HistoryCreate]) -> None:
        with self._session_factory() as session:
            self._apply_history_updates(session, user_id, reports)
            session.commit()

    def list_histories(self, user_id: int, filters: dict, page: int, page_size: int) -> dict[str, Any]:
        user_config = self._get_user_config(user_id)
        show_nsfw = user_config.get('showNsfw', False)
        effective_nsfw = resolve_effective_nsfw_filter(filters.get('nsfw', 'all'), show_nsfw)

        with self._session_factory() as session:
            conditions = [
                VideoHistory.user_id == user_id,
                exists(
                    select(1).select_from(Video).where(Video.id == VideoHistory.video_id),
                ),
            ]

            if filters.get('query'):
                search_clauses = build_video_search_clauses(
                    user_id=user_id,
                    query=filters['query'],
                    video_id_column=VideoHistory.video_id,
                )
                if search_clauses:
                    conditions.extend(search_clauses)

            if filters.get('video_id'):
                conditions.append(VideoHistory.video_id == filters['video_id'])
            if filters.get('min_duration'):
                conditions.append(VideoHistory.duration >= filters['min_duration'])
            if filters.get('start_date'):
                conditions.append(VideoHistory.end_time >= filters['start_date'])
            if filters.get('end_date'):
                conditions.append(VideoHistory.end_time <= filters['end_date'])
            if effective_nsfw == 'blocked':
                conditions.append(false())
            elif effective_nsfw != 'all':
                nsfw_history_exists = exists(
                    select(1)
                    .select_from(SubscriptionVideo)
                    .join(
                        UserSubscription,
                        UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
                    )
                    .where(
                        SubscriptionVideo.video_id == VideoHistory.video_id,
                        UserSubscription.user_id == user_id,
                        UserSubscription.is_nsfw,
                    ),
                )
                if effective_nsfw == 'yes':
                    conditions.append(nsfw_history_exists)
                elif effective_nsfw == 'no':
                    conditions.append(~nsfw_history_exists)
            if filters.get('site'):
                resolved_domains = SiteCatalog.resolve_domains(filters['site'])
                normalized_domains = [
                    domain
                    for domain in {url_helper.normalize_domain(raw_domain) for raw_domain in resolved_domains if raw_domain}
                    if domain
                ]
                if not normalized_domains:
                    return {
                        'items': [],
                        'total': 0,
                        'page': page,
                        'page_size': page_size,
                    }
                conditions.append(
                    exists(
                        select(1)
                        .select_from(Video)
                        .where(
                            and_(
                                Video.id == VideoHistory.video_id,
                                Video.domain.in_(normalized_domains),
                            ),
                        ),
                    ),
                )

            ranked_histories = (
                select(
                    VideoHistory.id.label('id'),
                    VideoHistory.end_time.label('end_time'),
                    func.row_number()
                    .over(
                        partition_by=VideoHistory.video_id,
                        order_by=(VideoHistory.end_time.desc(), VideoHistory.id.desc()),
                    )
                    .label('row_num'),
                )
                .where(*conditions)
                .subquery()
            )

            latest_history_ids = (
                select(
                    ranked_histories.c.id,
                    ranked_histories.c.end_time,
                )
                .where(ranked_histories.c.row_num == 1)
                .subquery()
            )

            total = session.scalar(
                select(func.count()).select_from(latest_history_ids),
            )

            histories = session.scalars(
                select(VideoHistory)
                .join(latest_history_ids, latest_history_ids.c.id == VideoHistory.id)
                .order_by(latest_history_ids.c.end_time.desc(), VideoHistory.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size),
            ).all()

            if not histories:
                return {
                    'items': [],
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                }

            video_ids = [h.video_id for h in histories]

            videos = session.scalars(
                select(Video).where(Video.id.in_(video_ids)),
            ).all()
            video_map = {v.id: v for v in videos}

            subs_links = session.scalars(
                select(SubscriptionVideo).where(SubscriptionVideo.video_id.in_(video_ids)),
            ).all()
            sub_ids = list(set(link.subscription_id for link in subs_links))

            subs = session.scalars(
                select(Subscription).where(Subscription.id.in_(sub_ids)),
            ).all()
            sub_map = {s.id: s for s in subs}

            user_subs = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id.in_(sub_ids),
                ),
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
                subs_for_video = _merge_profiles(
                    [
                        {
                            'id': s.id,
                            'name': s.name,
                            'url': s.url,
                            'type': s.type,
                            'avatar': s.avatar,
                            'is_nsfw': user_sub_nsfw_map.get(s.id, False),
                        }
                        for s in (video_subs.get(v.id) or [])
                        if s is not None
                    ],
                    _video_extra_profiles(v, 'subscriptions'),
                )

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
                    'played_at': h.end_time.strftime('%Y-%m-%d %H:%M:%S') if h.end_time else None,
                    'uploaded_at': v.publish_date.strftime('%Y-%m-%d %H:%M:%S') if v.publish_date else None,
                    'created_at': v.created_at.strftime('%Y-%m-%d %H:%M:%S') if v.created_at else None,
                    'subscriptions': subs_for_video,
                    'actors': _video_extra_profiles(v, 'actors'),
                    'site': video_site,
                }
                items.append(item)

            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
            }

    def get_videos_by_ids(self, user_id: int, video_ids: list[int]) -> list[VideoHistory]:
        with self._session_factory() as session:
            videos = session.scalars(
                select(VideoHistory).where(
                    VideoHistory.user_id == user_id,
                    VideoHistory.video_id.in_(video_ids),
                ),
            ).all()
            return videos

    def get_video_history(self, user_id: int, video_id: int) -> VideoHistory | None:
        with self._session_factory() as session:
            video_history = session.scalars(
                select(VideoHistory).where(
                    VideoHistory.user_id == user_id,
                    VideoHistory.video_id == video_id,
                ),
            ).first()
            return video_history

    def delete_history(self, user_id: int, history_id: int) -> int:
        with self._session_factory() as session:
            query_result = session.execute(
                delete(VideoHistory).where(
                    VideoHistory.id == history_id,
                    VideoHistory.user_id == user_id,
                ),
            )
            session.commit()
            return query_result.rowcount

    def clear_histories(self, user_id: int, video_ids: list[int] | None = None):
        with self._session_factory() as session:
            conditions = [VideoHistory.user_id == user_id]

            if video_ids:
                conditions.append(VideoHistory.video_id.in_(video_ids))

            query_result = session.execute(
                delete(VideoHistory).where(*conditions),
            )
            session.commit()
            return query_result.rowcount
