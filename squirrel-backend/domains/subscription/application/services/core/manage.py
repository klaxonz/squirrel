from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.listing.service import resolve_subscription_nsfw
from domains.subscription.application.services.core.runtime_models import SubscriptionMeta
from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription import ContentType, Subscription, build_subscription_canonical_key
from domains.user.domain.models.user import User
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session, register_after_commit
from infrastructure.site_catalog.url import resolve_site


class SubscriptionManageService:
    def __init__(
        self,
        session_factory=get_session,
        crud_service: SubscriptionCrudService | None = None,
        lifecycle: SubscriptionSyncLifecycle | None = None,
    ):
        self.session_factory = session_factory
        self.crud_service = crud_service or SubscriptionCrudService(session_factory=session_factory)
        self.lifecycle = lifecycle or SubscriptionSyncLifecycle(
            session_factory=session_factory,
            crud_service=self.crud_service,
        )

    @staticmethod
    def _detect_subscription_type(url: str) -> str:
        if ('youtube.com' in url or 'youtu.be' in url) and ('list=' in url or '/playlist?' in url):
            return ContentType.PLAYLIST

        if 'bilibili.com' in url:
            if '/favlist' in url or 'fid=' in url:
                return ContentType.PLAYLIST
            if '/season/' in url or 'season_id=' in url:
                return ContentType.PLAYLIST

        return ContentType.CHANNEL

    def create_subscription(
        self,
        user_id: int,
        subscribe_info: SubscriptionMeta,
        *,
        expected_intent_version: int | None = None,
    ) -> Subscription:
        with self.session_factory() as session:
            created_subscription = False
            canonical_key = build_subscription_canonical_key(subscribe_info.url)
            subscription_query = (
                select(Subscription)
                .where(
                    or_(
                        Subscription.canonical_key == canonical_key,
                        Subscription.url == subscribe_info.url,
                    ),
                )
                .order_by(Subscription.is_deleted.asc(), Subscription.id.asc())
                .with_for_update()
            )
            subscription = session.scalars(subscription_query).first()
            if subscription is None:
                candidate = Subscription(
                    type=self._detect_subscription_type(subscribe_info.url),
                    name=subscribe_info.name,
                    url=subscribe_info.url,
                    avatar=subscribe_info.avatar,
                    description=None,
                    extra_data={},
                )
                try:
                    with session.begin_nested():
                        session.add(candidate)
                        session.flush()
                    subscription = candidate
                    created_subscription = True
                except IntegrityError:
                    # Another request created the same canonical subscription while metadata
                    # was being fetched. Attach this user to the committed winner.
                    subscription = session.scalars(subscription_query).first()
                    if subscription is None:
                        raise

            user_subscription_query = (
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription.id,
                )
                .with_for_update()
            )
            user_subscription = session.scalars(
                user_subscription_query,
            ).first()
            activated = True
            if user_subscription and user_subscription.is_deleted:
                if (
                    expected_intent_version is not None
                    and user_subscription.intent_version != expected_intent_version
                ):
                    activated = False
                else:
                    user_subscription.is_deleted = False
                    user_subscription.intent_version += 1
            elif user_subscription:
                activated = True
            else:
                if expected_intent_version not in {None, 0}:
                    activated = False
                else:
                    candidate_user_subscription = UserSubscription(
                        user_id=user_id,
                        subscription_id=subscription.id,
                        intent_version=1,
                        is_nsfw=resolve_subscription_nsfw(subscribe_info.url),
                    )
                    try:
                        with session.begin_nested():
                            session.add(candidate_user_subscription)
                            session.flush()
                        user_subscription = candidate_user_subscription
                    except IntegrityError:
                        user_subscription = session.scalars(user_subscription_query).first()
                        if user_subscription is None:
                            raise
                        if (
                            user_subscription.is_deleted
                            and expected_intent_version is not None
                            and user_subscription.intent_version != expected_intent_version
                        ):
                            activated = False
                        elif user_subscription.is_deleted:
                            user_subscription.is_deleted = False
                            user_subscription.intent_version += 1
            if activated:
                subscription.is_deleted = False
            elif created_subscription:
                subscription.is_deleted = True
            session.commit()
        if activated:
            self.lifecycle.ensure_subscription_syncs(subscription.id, subscription.url)
        return subscription

    def restore_subscription(
        self,
        subscription_id: int,
        user_id: int,
        *,
        expected_intent_version: int | None = None,
    ) -> bool:
        with self.session_factory() as session:
            subscription = session.scalars(
                select(Subscription).where(Subscription.id == subscription_id).with_for_update(),
            ).first()
            if not subscription:
                return False

            user_subscription = session.scalars(
                select(UserSubscription)
                .where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.user_id == user_id,
                )
                .with_for_update(),
            ).first()

            if user_subscription and user_subscription.is_deleted:
                if (
                    expected_intent_version is not None
                    and user_subscription.intent_version != expected_intent_version
                ):
                    return False
                user_subscription.is_deleted = False
                user_subscription.intent_version += 1
            elif not user_subscription:
                if expected_intent_version not in {None, 0}:
                    return False
                user_subscription = UserSubscription(
                    subscription_id=subscription_id,
                    user_id=user_id,
                    is_deleted=False,
                    intent_version=1,
                    is_nsfw=resolve_subscription_nsfw(subscription.url),
                )
                session.add(user_subscription)

            subscription.is_deleted = False
            session.commit()
        subscription = self.crud_service.get_subscription_by_id(subscription_id)
        if subscription:
            self.lifecycle.ensure_subscription_syncs(subscription.id, subscription.url)
        return True

    def unsubscribe_by_id(self, user_id: int, subscription_id: int) -> bool:
        with self.session_factory() as session:
            if not subscription_id:
                return False

            subscription = session.scalars(
                select(Subscription).where(Subscription.id == subscription_id).with_for_update(),
            ).first()

            if not subscription:
                return False

            # 提交前查受影响 video_id:解绑后这些文档里的 subscription_names 会过时,
            # 需要重新构建文档(去掉已解绑的订阅名)。MEILISEARCH_URL 未配置时跳过。
            affected_video_ids: list[int] = []
            if settings.meili.url:
                affected_video_ids = session.scalars(
                    select(SubscriptionVideo.video_id).where(
                        SubscriptionVideo.subscription_id == subscription.id,
                    ),
                ).all()

            user_subscription = session.execute(
                select(UserSubscription).where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.subscription_id == subscription.id,
                    UserSubscription.is_deleted.is_(False),
                ),
            ).scalar_one_or_none()
            if not user_subscription:
                return False
            user_subscription.is_deleted = True
            user_subscription.intent_version += 1
            session.flush()

            has_other_subscribers = session.execute(
                select(UserSubscription.id)
                .where(
                    UserSubscription.subscription_id == subscription.id,
                    UserSubscription.user_id != user_id,
                    UserSubscription.is_deleted.is_(False),
                )
                .limit(1),
            ).first() is not None
            if has_other_subscribers:
                session.commit()
                return True

            subscription.is_deleted = True
            if affected_video_ids:

                def reindex_after_commit() -> None:
                    from domains.video.application.services.search.meili_indexer import get_meili_video_indexer

                    get_meili_video_indexer().reindex_video_ids(affected_video_ids)

                register_after_commit(
                    session,
                    reindex_after_commit,
                )
            session.commit()

        self.lifecycle.deactivate_subscription_syncs(
            subscription_id,
            reason='manual_unsubscribe',
        )

        return True

    def toggle_nsfw_status(self, user_id: int, subscription_id: int, is_nsfw: bool) -> bool:
        with self.session_factory() as session:
            user_sub = session.execute(
                select(UserSubscription).where(
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
                select(UserSubscription).where(
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
        canonical_key = build_subscription_canonical_key(url)
        with self.session_factory() as session:
            intent_version = session.execute(
                select(func.max(UserSubscription.intent_version))
                .join(Subscription, Subscription.id == UserSubscription.subscription_id)
                .where(
                    UserSubscription.user_id == user_id,
                    or_(Subscription.canonical_key == canonical_key, Subscription.url == url),
                ),
            ).scalar_one_or_none()
        payload = {
            'url': url,
            'user_id': user_id,
            'expected_intent_version': int(intent_version or 0),
        }
        site = resolve_site(url) or 'unknown'
        dedupe_key = (
            f'dedupe:subscription_import:{user_id}:{build_subscription_canonical_key(url)}:'
            f'{payload["expected_intent_version"]}'
        )
        try:
            _, task = crawl_task_service.create_job_with_task(
                job_type='subscription_import',
                source_type='manual',
                site=site,
                task_type='subscription_import',
                payload=payload,
                priority='manual',
                dedupe_key=dedupe_key,
                max_attempts=3,
            )
        except IntegrityError:
            with self.session_factory() as session:
                task = session.scalars(select(CrawlTask).where(CrawlTask.dedupe_key == dedupe_key)).first()
                if task is None:
                    raise
        return {'task_id': task.id, **payload}

    def list_user_ids(self) -> list[int]:
        with self.session_factory() as session:
            rows = session.execute(select(User.id).order_by(User.id.asc())).all()
            return [user_id for (user_id,) in rows]
