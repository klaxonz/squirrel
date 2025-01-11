from sqlalchemy import select

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
    with get_session() as session:
        subscription_video = SubscriptionVideo()
        subscription_video.subscription_id = subscription_id
        subscription_video.video_id = video_id
        session.add(subscription_video)
        session.commit()
        return subscription_video
