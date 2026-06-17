import logging
from collections.abc import Callable, Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.video.domain.junctions.video_creator import VideoCreator
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session as _default_get_session
from infrastructure.database.session import register_after_commit

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Generator[Session, None, None]]


def _reindex_video_safe(video_id: int, *, context: str) -> None:
    """creator 关联变更后重建 video 的 Meili 文档（creator_names 字段）；失败仅告警。

    Lazy import 避免 video application 层静态依赖造成循环。
    """
    try:
        from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
        get_meili_video_indexer().reindex_video_ids([video_id])
    except Exception:
        logger.warning(
            'meili reindex_video_ids failed context=%s video_id=%s (full reindex will catch up)',
            context, video_id, exc_info=True,
        )


class VideoCreatorService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def get_video_creator(self, video_id: int, creator_id: int) -> VideoCreator | None:
        with self._session_factory() as session:
            video_creator = session.scalars(select(VideoCreator).where(
                VideoCreator.video_id == video_id,
                VideoCreator.creator_id == creator_id)).first()
            return video_creator

    def create_video_creator(self, video_id: int, creator_id: int) -> VideoCreator:
        with self._session_factory() as session:
            video_creator = VideoCreator(video_id=video_id, creator_id=creator_id)
            session.add(video_creator)
            # 新建关联会改变 Meili 文档的 creator_names 字段，提交后重建文档。
            # 必须在 commit 前注册。MEILISEARCH_URL 未配置时跳过。
            if settings.meili.url:
                register_after_commit(
                    session,
                    lambda: _reindex_video_safe(video_id, context='creator_link'),
                )
            session.commit()
            return video_creator


video_creator_service = VideoCreatorService()
get_video_creator = video_creator_service.get_video_creator
create_video_creator = video_creator_service.create_video_creator
