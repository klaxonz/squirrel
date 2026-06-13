from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

import domains.user.application.services.feed as user_video_feed_service
from infrastructure.database.session import get_session
from domains.video.domain.junctions.subscription_video import SubscriptionVideo


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
            session.commit()
            if row is not None:
                # 新建时直接返回对象
                if refresh_feed:
                    user_video_feed_service.add_video_to_active_subscribers(subscription_id, video_id)
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
