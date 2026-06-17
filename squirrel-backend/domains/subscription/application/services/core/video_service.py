import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session, register_after_commit

logger = logging.getLogger(__name__)


def _reindex_videos_safe(video_ids: list[int], *, context: str, subscription_id: int | None = None) -> None:
    """关联变更后重建受影响 video 的 Meili 文档；失败仅告警（全量重建兜底）。

    Lazy import 避免 subscription 域静态依赖 video application 层造成循环导入。
    """
    try:
        from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
        get_meili_video_indexer().reindex_video_ids(video_ids)
    except Exception:
        logger.warning(
            'meili reindex_video_ids failed context=%s subscription_id=%s count=%d (full reindex will catch up)',
            context, subscription_id, len(video_ids), exc_info=True,
        )


class SubscriptionVideoService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

    def get_subscription_video_by_video_id(self, video_id: int) -> SubscriptionVideo | None:
        with self.session_factory() as session:
            subscription_video = session.scalars(select(SubscriptionVideo).where(SubscriptionVideo.video_id == video_id)).first()
            return subscription_video

    def get_subscription_video(self, subscription_id: int, video_id: int) -> SubscriptionVideo | None:
        with self.session_factory() as session:
            return session.scalars(select(SubscriptionVideo).where(
                SubscriptionVideo.subscription_id == subscription_id,
                SubscriptionVideo.video_id == video_id)).first()

    def create_subscription_video(
        self,
        subscription_id: int,
        video_id: int,
        *,
        refresh_feed: bool = True,
    ) -> tuple[SubscriptionVideo | None, bool]:
        """Idempotently create subscription-video association. Returns (obj, created)."""
        with self.session_factory() as session:
            stmt = (
                pg_insert(SubscriptionVideo)
                .values(subscription_id=subscription_id, video_id=video_id)
                .on_conflict_do_nothing()
                .returning(SubscriptionVideo.subscription_id, SubscriptionVideo.video_id)
            )
            result = session.execute(stmt)
            row = result.first()
            # 新建关联会改变 Meili 文档的 subscription_names 字段，提交后重建文档。
            # 必须在 commit 前注册（after_commit 事件在 commit 时 fire），否则回调永不执行。
            # 提交后重建。
            created = row is not None
            if created and settings.meili.url:
                register_after_commit(
                    session,
                    lambda: _reindex_videos_safe([video_id], context='subscription_link', subscription_id=subscription_id),
                )
            session.commit()
            if row is not None:
                # 新建时直接返回对象
                return session.scalars(select(SubscriptionVideo).where(
                    SubscriptionVideo.subscription_id == subscription_id,
                    SubscriptionVideo.video_id == video_id,
                )).first(), True
            # 已存在：查询并返回
            return session.scalars(select(SubscriptionVideo).where(
                SubscriptionVideo.subscription_id == subscription_id,
                SubscriptionVideo.video_id == video_id,
            )).first(), False


subscription_video_service = SubscriptionVideoService()
get_subscription_video_by_video_id = subscription_video_service.get_subscription_video_by_video_id
get_subscription_video = subscription_video_service.get_subscription_video
create_subscription_video = subscription_video_service.create_subscription_video
