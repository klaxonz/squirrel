from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session, register_after_commit


class SubscriptionVideoService:
    def __init__(self, session_factory=get_session):
        self.session_factory = session_factory

    def get_subscription_video_by_video_id(self, video_id: int) -> SubscriptionVideo | None:
        with self.session_factory() as session:
            subscription_video = session.scalars(
                select(SubscriptionVideo).where(SubscriptionVideo.video_id == video_id)
            ).first()
            return subscription_video

    def get_subscription_video(self, subscription_id: int, video_id: int) -> SubscriptionVideo | None:
        with self.session_factory() as session:
            return session.scalars(
                select(SubscriptionVideo).where(
                    SubscriptionVideo.subscription_id == subscription_id, SubscriptionVideo.video_id == video_id
                )
            ).first()

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
            # 新建关联会改变 Meili 文档的 subscription_names 字段,提交后重建文档。
            # 必须在 commit 前注册(after_commit 事件在 commit 时 fire),否则回调永不执行。
            # 提交后重建。
            created = row is not None
            if created and settings.meili.url:

                def reindex_after_commit() -> None:
                    from domains.video.application.services.search.meili_indexer import get_meili_video_indexer

                    get_meili_video_indexer().reindex_video_ids([video_id])

                register_after_commit(
                    session,
                    reindex_after_commit,
                )
            session.commit()
            if row is not None:
                # 新建时直接返回对象
                return session.scalars(
                    select(SubscriptionVideo).where(
                        SubscriptionVideo.subscription_id == subscription_id,
                        SubscriptionVideo.video_id == video_id,
                    )
                ).first(), True
            # 已存在:查询并返回
            return session.scalars(
                select(SubscriptionVideo).where(
                    SubscriptionVideo.subscription_id == subscription_id,
                    SubscriptionVideo.video_id == video_id,
                )
            ).first(), False


subscription_video_service = SubscriptionVideoService()
get_subscription_video_by_video_id = subscription_video_service.get_subscription_video_by_video_id
get_subscription_video = subscription_video_service.get_subscription_video
create_subscription_video = subscription_video_service.create_subscription_video
