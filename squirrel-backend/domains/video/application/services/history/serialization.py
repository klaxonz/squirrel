from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.extraction.thumbnail_downloader import thumbnail_downloader_service
from domains.video.application.services.listing.profiles import merge_profiles, video_extra_profiles
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory
from infrastructure.site_catalog.url import get_site_from_url


def serialize_history_items(session: Session, user_id: int, histories: list[VideoHistory]) -> list[dict[str, Any]]:
    if not histories:
        return []

    video_ids = [history.video_id for history in histories]

    videos = session.scalars(
        select(Video).where(Video.id.in_(video_ids)),
    ).all()
    video_map = {video.id: video for video in videos}

    subs_links = session.scalars(
        select(SubscriptionVideo).where(SubscriptionVideo.video_id.in_(video_ids)),
    ).all()
    sub_ids = list(set(link.subscription_id for link in subs_links))

    subs = session.scalars(
        select(Subscription).where(Subscription.id.in_(sub_ids)),
    ).all()
    sub_map = {subscription.id: subscription for subscription in subs}

    user_subs = session.scalars(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.subscription_id.in_(sub_ids),
        ),
    ).all()
    user_sub_nsfw_map = {user_sub.subscription_id: user_sub.is_nsfw for user_sub in user_subs}

    video_subs: dict[int, list[Subscription | None]] = {}
    for link in subs_links:
        video_subs.setdefault(link.video_id, []).append(sub_map.get(link.subscription_id))

    items = []
    for history in histories:
        video = video_map.get(history.video_id)
        if not video:
            continue

        subs_for_video = merge_profiles(
            [
                {
                    'id': subscription.id,
                    'name': subscription.name,
                    'url': subscription.url,
                    'type': subscription.type,
                    'avatar': subscription.avatar,
                    'is_nsfw': user_sub_nsfw_map.get(subscription.id, False),
                }
                for subscription in (video_subs.get(video.id) or [])
                if subscription is not None
            ],
            video_extra_profiles(video, 'subscriptions'),
        )

        video_site = get_site_from_url(video.url)
        if not video_site and subs_for_video:
            for sub_info in subs_for_video:
                sub_url = sub_info.get('url')
                if sub_url:
                    video_site = get_site_from_url(sub_url)
                    if video_site:
                        break

        items.append({
            'id': video.id,
            'history_id': history.id,
            'title': video.title,
            'url': video.url,
            'thumbnail': thumbnail_downloader_service.get_thumbnail_url(video.id, video.thumbnail, video.url),
            'duration': video.duration,
            'last_position': history.last_position or 0,
            'played_at': history.end_time.strftime('%Y-%m-%d %H:%M:%S') if history.end_time else None,
            'uploaded_at': video.publish_date.strftime('%Y-%m-%d %H:%M:%S') if video.publish_date else None,
            'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S') if video.created_at else None,
            'subscriptions': subs_for_video,
            'actors': video_extra_profiles(video, 'actors'),
            'site': video_site,
        })
    return items
