from typing import Optional, List

from sqlalchemy import select, func, and_, exists

from models.video import Video
from models.links import SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from utils import url_helper


def build_base_video_query(
        user_id: int,
        show_nsfw: bool,
        subscription_id: Optional[int] = None,
        query: Optional[str] = None,
        nsfw: str = 'all',
        domains: Optional[List[str]] = None
):
    """构建基础视频查询，以 Video 为主表。"""
    base_query = (
        select(Video, SubscriptionVideo.subscription_id.label('subscription_id'))
        .select_from(Video)
        .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
        .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            and_(
                Video.is_deleted == False,
                UserSubscription.is_deleted == False,
                Subscription.is_deleted == False,
                UserSubscription.user_id == user_id
            )
        )
    )

    if subscription_id:
        base_query = base_query.where(SubscriptionVideo.subscription_id == subscription_id)

    if nsfw == 'yes':
        base_query = base_query.where(UserSubscription.is_nsfw == True)
    elif nsfw == 'no':
        base_query = base_query.where(UserSubscription.is_nsfw == False)
    else:
        if not show_nsfw:
            base_query = base_query.where(UserSubscription.is_nsfw == False)

    if query:
        base_query = base_query.where(Video.title.like(f"%{query}%"))

    if domains:
        normalized_domains = [
            d for d in {url_helper.normalize_domain(domain) for domain in domains if domain} if d
        ]
        if normalized_domains:
            base_query = base_query.where(Video.domain.in_(normalized_domains))

    return base_query


def category_predicate(user_id: int, category: Optional[str]):
    """返回分类筛选条件，复用在列表/计数/随机。"""
    published = Video.publish_date <= func.now()

    if category == 'preview':
        return Video.publish_date > func.now()
    if category == 'read':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == Video.id
                    )
                )
            )
        )
    if category == 'unread':
        return and_(
            published,
            ~exists(
                select(1).where(
                    and_(
                        VideoHistory.user_id == user_id,
                        VideoHistory.video_id == Video.id
                    )
                )
            )
        )
    if category == 'liked':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == Video.id,
                        VideoInteraction.interaction_type == 1
                    )
                )
            )
        )
    if category == 'later':
        return and_(
            published,
            exists(
                select(1).where(
                    and_(
                        VideoInteraction.user_id == user_id,
                        VideoInteraction.video_id == Video.id,
                        VideoInteraction.interaction_type == 3
                    )
                )
            )
        )

    return published


def resolve_sort_column(sort_by: str):
    if sort_by == 'created_at':
        return Video.created_at
    return Video.publish_date
