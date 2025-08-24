from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.database import get_session
from models.links import SubscriptionVideo


def get_subscription_video_by_video_id(video_id: int):
    with get_session() as session:
        subscription_video = session.scalars(select(SubscriptionVideo).where(SubscriptionVideo.video_id == video_id)).first()
        return subscription_video


def get_subscription_video(subscription_id, video_id):
    with get_session() as session:
        return session.scalars(select(SubscriptionVideo).where(
            SubscriptionVideo.subscription_id == subscription_id,
            SubscriptionVideo.video_id == video_id)).first()


def create_subscription_video(subscription_id, video_id):
    """幂等创建订阅-视频关联。返回 (obj, created)。"""
    with get_session() as session:
        stmt = (
            pg_insert(SubscriptionVideo)
            .values(subscription_id=subscription_id, video_id=video_id)
            .on_conflict_do_nothing()
            .returning(SubscriptionVideo.subscription_id, SubscriptionVideo.video_id)
        )
        result = session.execute(stmt)
        created = result.rowcount and result.rowcount > 0
        session.commit()
        if created:
            # 新建时直接返回对象
            return session.scalars(select(SubscriptionVideo).where(
                SubscriptionVideo.subscription_id == subscription_id,
                SubscriptionVideo.video_id == video_id
            )).first(), True
        # 已存在：查询并返回
        return session.scalars(select(SubscriptionVideo).where(
            SubscriptionVideo.subscription_id == subscription_id,
            SubscriptionVideo.video_id == video_id
        )).first(), False
