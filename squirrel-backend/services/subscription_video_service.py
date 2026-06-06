from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database import get_session
from models.links import SubscriptionVideo
from services import user_video_feed_service


def get_subscription_video_by_video_id(video_id: int) -> Optional[SubscriptionVideo]:
    with get_session() as session:
        subscription_video = session.scalars(select(SubscriptionVideo).where(SubscriptionVideo.video_id == video_id)).first()
        return subscription_video


def get_subscription_video(subscription_id: int, video_id: int) -> Optional[SubscriptionVideo]:
    with get_session() as session:
        return session.scalars(select(SubscriptionVideo).where(
            SubscriptionVideo.subscription_id == subscription_id,
            SubscriptionVideo.video_id == video_id)).first()


def create_subscription_video(subscription_id: int, video_id: int) -> Tuple[Optional[SubscriptionVideo], bool]:
    """幂等创建订阅-视频关联。返回 (obj, created)。"""
    with get_session() as session:
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
            user_video_feed_service.add_video_to_active_subscribers(subscription_id, video_id)
            return session.scalars(select(SubscriptionVideo).where(
                SubscriptionVideo.subscription_id == subscription_id,
                SubscriptionVideo.video_id == video_id
            )).first(), True
        # 已存在：查询并返回
        return session.scalars(select(SubscriptionVideo).where(
            SubscriptionVideo.subscription_id == subscription_id,
            SubscriptionVideo.video_id == video_id
        )).first(), False
