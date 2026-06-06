from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select

from core.database import get_session
from models.video import Video
from utils import url_helper


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


def create_video(
    url: str,
    title: str,
    publish_date: datetime,
    thumbnail: str,
    duration: int
) -> Video:
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


def _parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    try:
        return datetime.fromisoformat(normalized.replace('Z', '+00:00'))
    except ValueError:
        return None


def save_remote_video(data: dict) -> Video:
    url = str(data.get('url') or '').strip()
    title = str(data.get('title') or '').strip()
    if not url:
        raise ValueError('url is required')
    if not title:
        raise ValueError('title is required')

    with get_session() as session:
        video = session.scalars(select(Video).where(Video.url == url)).first()
        if video:
            return video

        publish_date = _parse_optional_datetime(data.get('publish_date') or data.get('uploaded_at'))
        extra_data = {
            'source': 'remote',
            'site': data.get('site') or None,
            'subscriptions': data.get('subscriptions') or [],
            'actors': data.get('actors') or [],
        }

        video = Video(
            url=url,
            domain=url_helper.normalize_domain(url),
            title=title,
            publish_date=publish_date,
            thumbnail=data.get('thumbnail') or None,
            duration=data.get('duration'),
            description=data.get('description') or None,
            extra_data=extra_data,
        )
        session.add(video)
        session.commit()
        session.refresh(video)
        return video