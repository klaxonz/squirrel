import logging
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_, case
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload, with_loader_criteria

from core.database import get_session
from models.creator import Creator
from models.links import SubscriptionVideo, UserSubscription, VideoCreator
from models.subscription import Subscription
from models.video import Video
from models.video_clip_marker import VideoClipMarker
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from services import user_config_service
from services.video_clip_marker_service import serialize_marker
from services.video_list_query_service import (
    _build_feed_rows_query,
    _build_list_query,
    _fetch_feed_page_video_ids,
)
from core.extraction.services.thumbnail_downloader import thumbnail_downloader_service
from utils import url_helper

logger = logging.getLogger(__name__)


def _elapsed_ms(start_time: float) -> float:
    return round((perf_counter() - start_time) * 1000, 3)


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


def get_video(user_id: int, video_id: int) -> Optional[Dict[str, Any]]:
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

        def _history_sort_key(history: VideoHistory) -> Any:
            return history.updated_at or history.end_time or history.created_at

        def _interaction_sort_key(interaction: VideoInteraction) -> Any:
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