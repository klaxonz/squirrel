import json
import logging
from typing import Any

from sqlalchemy import select

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
from domains.subscription.application.services.core.crud import subscription_crud_service
from domains.subscription.application.services.core.listing.service import resolve_subscription_nsfw
from domains.subscription.application.services.core.runtime_models import SubscriptionMeta
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import ContentType, Subscription
from domains.system.domain.models import constants
from domains.user.domain.models.user import User
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session, register_after_commit
from infrastructure.messaging.framework.producer import RedisStreamProducer
from infrastructure.messaging.models.message import Message

logger = logging.getLogger(__name__)


def _reindex_videos_safe(video_ids: list[int], *, context: str, subscription_id: int | None = None) -> None:
    """解绑后重建受影响 video 的 Meili 文档；失败仅告警（全量重建兜底）。

    Lazy import 避免subscription 域静态依赖 video application 层造成循环导入。
    """
    try:
        from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
        get_meili_video_indexer().reindex_video_ids(video_ids)
    except Exception:
        logger.warning(
            'meili reindex_video_ids failed context=%s subscription_id=%s count=%d (full reindex will catch up)',
            context, subscription_id, len(video_ids), exc_info=True,
        )


class SubscriptionManageService:
    def __init__(self, session_factory=get_session, crud_service=None, sync_state_service=None):
        self.session_factory = session_factory
        self.crud_service = crud_service or subscription_crud_service
        self.sync_state_service = sync_state_service or subscription_sync_state_service

    @staticmethod
    def _detect_subscription_type(url: str) -> str:
        if 'youtube.com' in url or 'youtu.be' in url:
            if 'list=' in url or '/playlist?' in url:
                return ContentType.PLAYLIST

        if 'bilibili.com' in url:
            if '/favlist' in url or 'fid=' in url:
                return ContentType.PLAYLIST
            if '/season/' in url or 'season_id=' in url:
                return ContentType.PLAYLIST

        return ContentType.CHANNEL

    def create_subscription(self, user_id: int, subscribe_info: SubscriptionMeta) -> Subscription:
        with self.session_factory() as session:
            user_subscription = None
            subscription = self.crud_service.get_subscription_by_url_and_name(url=subscribe_info.url, name=subscribe_info.name)
            if subscription:
                self.sync_state_service.ensure_sync_states(subscription.id, subscription.url)
                return subscription
            content_type = self._detect_subscription_type(subscribe_info.url)

            subscription = Subscription(
                type=content_type,
                name=subscribe_info.name,
                url=subscribe_info.url,
                avatar=subscribe_info.avatar,
                description=None,
                extra_data={},
            )
            session.add(subscription)
            session.flush()
            user_subscription = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription.id,
                )).first()
            if not user_subscription:
                is_nsfw = resolve_subscription_nsfw(subscribe_info.url)

                user_subscription = UserSubscription(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    is_nsfw=is_nsfw,
                )
                session.add(user_subscription)
            session.commit()
        if user_subscription is not None:
            self.sync_state_service.ensure_sync_states(subscription.id, subscription.url)
        return subscription

    def restore_subscription(self, subscription_id: int, user_id: int) -> None:
        with self.session_factory() as session:
            subscription = session.get(Subscription, subscription_id)
            if not subscription:
                return

            subscription.is_deleted = False

            user_subscription = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.user_id == user_id,
                ),
            ).first()

            if user_subscription and user_subscription.is_deleted:
                user_subscription.is_deleted = False
            elif not user_subscription:
                user_subscription = UserSubscription(
                    subscription_id=subscription_id,
                    user_id=user_id,
                    is_deleted=False,
                    is_nsfw=False,
                )
                session.add(user_subscription)

            session.commit()
        subscription = self.crud_service.get_subscription_by_id(subscription_id)
        if subscription:
            self.sync_state_service.ensure_sync_states(subscription.id, subscription.url)

    def unsubscribe_by_id(self, user_id: int, subscription_id: int) -> bool:
        with self.session_factory() as session:
            if not subscription_id:
                return False

            subscription = session.scalars(
                select(Subscription).where(Subscription.id == subscription_id),
            ).first()

            if not subscription:
                return False

            # 提交前查受影响 video_id：解绑后这些文档里的 subscription_names 会过时，
            # 需要重新构建文档（去掉已解绑的订阅名）。MEILISEARCH_URL 未配置时跳过。
            affected_video_ids: list[int] = []
            if settings.MEILISEARCH_URL:
                affected_video_ids = session.scalars(
                    select(SubscriptionVideo.video_id).where(
                        SubscriptionVideo.subscription_id == subscription.id,
                    ),
                ).all()

            active_user_subscriptions = session.scalars(
                select(UserSubscription).where(
                    UserSubscription.subscription_id == subscription.id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).all()

            for user_subscription in active_user_subscriptions:
                user_subscription.is_deleted = True

            subscription.is_deleted = True
            if affected_video_ids:
                register_after_commit(
                    session,
                    lambda: _reindex_videos_safe(affected_video_ids, context='unsubscribe', subscription_id=subscription.id),
                )
            session.commit()

        self.sync_state_service.deactivate_sync_states(
            subscription_id,
            reason='manual_unsubscribe',
        )

        return True

    def toggle_nsfw_status(self, user_id: int, subscription_id: int, is_nsfw: bool) -> bool:
        with self.session_factory() as session:
            user_sub = session.execute(
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).scalar_one_or_none()
            if not user_sub:
                return False

            user_sub.is_nsfw = is_nsfw
            session.commit()
        return True

    def toggle_special_follow_status(self, user_id: int, subscription_id: int, is_special_followed: bool) -> bool:
        with self.session_factory() as session:
            user_sub = session.execute(
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).scalar_one_or_none()
            if not user_sub:
                return False

            user_sub.is_special_followed = is_special_followed
            session.commit()
        return True

    def create_subscribe_message(self, url: str, user_id: int) -> dict[str, Any]:
        with self.session_factory() as session:
            task = {
                'url': url,
                'user_id': user_id,
            }
            message = Message(body=json.dumps(task))
            session.add(message)
            session.commit()
            dump_json = message.to_dict()
            RedisStreamProducer().send(constants.QUEUE_SUBSCRIBE, dump_json)
        return dump_json

    def list_user_ids(self) -> list[int]:
        with self.session_factory() as session:
            rows = session.execute(select(User.id).order_by(User.id.asc())).all()
            return [user_id for user_id, in rows]


subscription_manage_service = SubscriptionManageService()
create_subscription = subscription_manage_service.create_subscription
restore_subscription = subscription_manage_service.restore_subscription
unsubscribe_by_id = subscription_manage_service.unsubscribe_by_id
toggle_nsfw_status = subscription_manage_service.toggle_nsfw_status
toggle_special_follow_status = subscription_manage_service.toggle_special_follow_status
create_subscribe_message = subscription_manage_service.create_subscribe_message
list_user_ids = subscription_manage_service.list_user_ids
