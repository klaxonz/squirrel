import logging
from collections.abc import Callable, Generator
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

import infrastructure.site_catalog.url as url_helper
from domains.video.domain.models.video import Video
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session as _default_get_session
from infrastructure.database.session import register_after_commit

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Generator[Session, None, None]]


def _index_video_after_commit(session: Session, video_id: int) -> None:
    """事务提交后把 video 推到 Meilisearch(增量直写,失败仅告警)。

    与 video_persistence._index_video_after_commit 同构,供本模块的写入路径复用。
    """
    if not settings.meili.url:
        return
    try:
        register_after_commit(session, lambda: _upsert_video_safe(video_id))
    except Exception:
        logger.warning('meili index register failed video_id=%s', video_id, exc_info=True)


def _upsert_video_safe(video_id: int) -> None:
    """Lazy import 避免 crud 与 meili_indexer 之间的潜在循环依赖。"""
    try:
        from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
        get_meili_video_indexer().upsert_safe(video_id)
    except Exception:
        logger.warning('meili upsert_safe failed video_id=%s (full reindex will catch up)', video_id, exc_info=True)


class VideoCrudService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def get_video_by_url(self, url: str) -> Video:
        with self._session_factory() as session:
            video = session.scalars(select(Video).where(Video.url == url)).first()
            return video

    def get_videos_by_urls(self, urls: list[str]) -> dict[str, Video]:
        if not urls:
            return {}
        with self._session_factory() as session:
            rows = session.scalars(
                select(Video).where(Video.url.in_(urls)),
            ).all()
            return {video.url: video for video in rows}

    def get_video_by_id(self, video_id: int) -> Video:
        with self._session_factory() as session:
            video = session.get(Video, video_id)
            return video

    def create_video(
        self,
        url: str,
        title: str,
        publish_date: datetime,
        thumbnail: str,
        duration: int,
    ) -> Video:
        with self._session_factory() as session:
            video = Video()
            video.url = url
            video.domain = url_helper.normalize_domain(url)
            video.title = title
            video.publish_date = publish_date
            video.thumbnail = thumbnail
            video.duration = duration
            session.add(video)
            session.flush()  # 拿到 video.id 再注册 after_commit 回调
            _index_video_after_commit(session, video.id)
            session.commit()
            return video

    @staticmethod
    def _parse_optional_datetime(value: str | None) -> datetime | None:
        if not value:
            return None

        normalized = str(value).strip()
        if not normalized:
            return None

        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            return None

    def save_remote_video(self, data: dict) -> Video:
        url = str(data.get("url") or "").strip()
        title = str(data.get("title") or "").strip()
        if not url:
            raise ValueError("url is required")
        if not title:
            raise ValueError("title is required")

        with self._session_factory() as session:
            video = session.scalars(select(Video).where(Video.url == url)).first()
            if video:
                return video

            publish_date = self._parse_optional_datetime(data.get("publish_date") or data.get("uploaded_at"))
            extra_data = {
                "source": "remote",
                "site": data.get("site") or None,
                "subscriptions": data.get("subscriptions") or [],
                "actors": data.get("actors") or [],
            }

            video = Video(
                url=url,
                domain=url_helper.normalize_domain(url),
                title=title,
                publish_date=publish_date,
                thumbnail=data.get("thumbnail") or None,
                duration=data.get("duration"),
                description=data.get("description") or None,
                extra_data=extra_data,
            )
            session.add(video)
            session.flush()
            _index_video_after_commit(session, video.id)
            session.commit()
            session.refresh(video)
            return video


video_crud_service = VideoCrudService()
get_video_by_url = video_crud_service.get_video_by_url
get_videos_by_urls = video_crud_service.get_videos_by_urls
get_video_by_id = video_crud_service.get_video_by_id
create_video = video_crud_service.create_video
save_remote_video = video_crud_service.save_remote_video
