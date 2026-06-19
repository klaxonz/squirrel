from collections.abc import Callable, Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.video.domain.junctions.video_creator import VideoCreator
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session as _default_get_session
from infrastructure.database.session import register_after_commit

SessionFactory = Callable[[], Generator[Session, None, None]]


class VideoCreatorService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def get_video_creator(self, video_id: int, creator_id: int) -> VideoCreator | None:
        with self._session_factory() as session:
            video_creator = session.scalars(
                select(VideoCreator).where(VideoCreator.video_id == video_id, VideoCreator.creator_id == creator_id)
            ).first()
            return video_creator

    def create_video_creator(self, video_id: int, creator_id: int) -> VideoCreator:
        with self._session_factory() as session:
            video_creator = VideoCreator(video_id=video_id, creator_id=creator_id)
            session.add(video_creator)
            # 新建关联会改变 Meili 文档的 creator_names 字段,提交后重建文档。
            # 必须在 commit 前注册。MEILISEARCH_URL 未配置时跳过。
            if settings.meili.url:

                def reindex_after_commit() -> None:
                    from domains.video.application.services.search.meili_indexer import get_meili_video_indexer

                    get_meili_video_indexer().reindex_video_ids([video_id])

                register_after_commit(
                    session,
                    reindex_after_commit,
                )
            session.commit()
            return video_creator


video_creator_service = VideoCreatorService()
get_video_creator = video_creator_service.get_video_creator
create_video_creator = video_creator_service.create_video_creator
