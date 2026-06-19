import logging
from typing import Any

from sqlalchemy import and_, case, false, func, literal, or_, select

import domains.user.application.services.config as user_config_service
from domains.subscription.application.services.core.listing.enrichment import (
    load_recent_videos,
    load_subscription_extract_counts,
    load_subscription_unread_counts,
)
from domains.subscription.application.services.core.listing.search import build_subscription_search_clauses, contains
from domains.subscription.application.services.core.listing.serialization import serialize_subscription_list_item
from domains.subscription.application.services.core.listing.site import resolve_site_slug
from domains.subscription.application.services.core.listing.site import (
    resolve_subscription_nsfw as resolve_subscription_nsfw_by_url,
)
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from domains.subscription.interfaces.dto.subscription_dto import SubscriptionDto
from domains.video.application.services.moderation.nsfw_policy import resolve_effective_nsfw_filter
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from infrastructure.database.session import get_session

logger = logging.getLogger(__name__)


class SubscriptionListService:
    def __init__(self, session_factory=get_session, get_user_config=None):
        self.session_factory = session_factory
        self.get_user_config = get_user_config or user_config_service.get_config

    def list_subscriptions(
        self,
        user_id: int,
        query: str | None,
        type: str | None,
        nsfw: str,
        page: int,
        page_size: int,
        domains: list[str] | None = None,
        special: str = 'all',
    ) -> tuple[list[dict[str, Any]], int]:
        user_config = self.get_user_config(user_id)
        show_nsfw = user_config.get('showNsfw', False)

        with self.session_factory() as session:
            conditions: list[Any] = [
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
            ]

            if type:
                conditions.append(Subscription.type == type)

            effective_nsfw = resolve_effective_nsfw_filter(nsfw, show_nsfw)

            if effective_nsfw == 'blocked':
                conditions.append(false())
            elif effective_nsfw == 'yes':
                conditions.append(UserSubscription.is_nsfw.is_(True))
            elif effective_nsfw == 'no':
                conditions.append(UserSubscription.is_nsfw.is_(False))

            if special == 'yes':
                conditions.append(UserSubscription.is_special_followed.is_(True))
            elif special == 'no':
                conditions.append(UserSubscription.is_special_followed.is_(False))

            if domains:
                normalized_domains = [domain for domain in dict.fromkeys(domains) if domain]
                if normalized_domains:
                    conditions.append(
                        or_(*[contains(Subscription.url, domain) for domain in normalized_domains]),
                    )

            conditions.extend(build_subscription_search_clauses(query))

            count_statement = (
                select(func.count())
                .select_from(UserSubscription)
                .join(Subscription, Subscription.id == UserSubscription.subscription_id)
                .where(*conditions)
            )
            total_count = session.execute(count_statement).scalar() or 0

            statement = (
                select(
                    Subscription.id,
                    Subscription.type,
                    Subscription.name,
                    Subscription.url,
                    Subscription.avatar,
                    Subscription.description,
                    func.coalesce(Subscription.total_videos, 0).label('total_videos'),
                    Subscription.is_deleted,
                    Subscription.extra_data,
                    Subscription.created_at,
                    Subscription.updated_at,
                    UserSubscription.is_nsfw.label('is_nsfw'),
                    UserSubscription.is_special_followed.label('is_special_followed'),
                    literal(0).label('total_extract'),
                    func.coalesce(SubscriptionSyncState.sync_status, 'idle').label('sync_status'),
                    SubscriptionSyncState.last_sync_at.label('last_sync_at'),
                    SubscriptionSyncState.last_success_at.label('last_success_at'),
                    SubscriptionSyncState.next_sync_at.label('next_sync_at'),
                    SubscriptionSyncState.last_error.label('last_error'),
                    func.coalesce(SubscriptionSyncState.pending_video_count, 0).label('pending_video_count'),
                )
                .select_from(UserSubscription)
                .join(Subscription, Subscription.id == UserSubscription.subscription_id)
                .outerjoin(
                    SubscriptionSyncState,
                    and_(
                        SubscriptionSyncState.subscription_id == Subscription.id,
                        SubscriptionSyncState.sync_mode == SyncMode.INCREMENTAL.value,
                    ),
                )
                .where(*conditions)
                .order_by(UserSubscription.is_special_followed.desc(), Subscription.created_at.desc())
                .limit(page_size)
                .offset((page - 1) * page_size)
            )

            results = session.execute(statement).mappings().all()
            subscription_ids = [int(row['id']) for row in results]
            extract_count_map = load_subscription_extract_counts(session, subscription_ids)
            unread_count_map = load_subscription_unread_counts(session, user_id, subscription_ids)
            recent_videos_map = load_recent_videos(session, subscription_ids)

            subscriptions = []
            for row_mapping in results:
                sub_id = int(row_mapping['id'])
                total_extract = extract_count_map.get(sub_id, 0)
                unread_count = unread_count_map.get(sub_id, 0)
                recent_videos = recent_videos_map.get(sub_id, [])
                subscriptions.append(
                    serialize_subscription_list_item(row_mapping, total_extract, recent_videos, unread_count)
                )

            return subscriptions, total_count

    def get_subscription_detail(self, subscription_id: int) -> SubscriptionDto | None:
        with self.session_factory() as session:
            video_count_subq = (
                select(func.count(SubscriptionVideo.video_id))
                .where(SubscriptionVideo.subscription_id == Subscription.id)
                .correlate(Subscription)
                .scalar_subquery()
            )
            # 与裸 SQL 对齐:subscription 列 + total_videos 用 max(total_videos, video_count) 覆盖,
            # 附加 sync_state 列 + 合成的 is_nsfw/is_special_followed(详情视图无 per-user 上下文)。
            effective_total = case(
                (func.coalesce(video_count_subq, 0) > Subscription.total_videos, func.coalesce(video_count_subq, 0)),
                else_=Subscription.total_videos,
            )
            row = (
                session.execute(
                    select(
                        Subscription.id,
                        Subscription.type,
                        Subscription.name,
                        Subscription.url,
                        Subscription.avatar,
                        Subscription.description,
                        effective_total.label('total_videos'),
                        Subscription.is_deleted,
                        Subscription.extra_data,
                        Subscription.created_at,
                        Subscription.updated_at,
                        literal(0).label('is_nsfw'),
                        literal(0).label('is_special_followed'),
                        func.coalesce(video_count_subq, 0).label('total_extract'),
                        func.coalesce(SubscriptionSyncState.sync_status, SyncStatus.IDLE.value).label('sync_status'),
                        SubscriptionSyncState.last_sync_at.label('last_sync_at'),
                        SubscriptionSyncState.last_success_at.label('last_success_at'),
                        SubscriptionSyncState.next_sync_at.label('next_sync_at'),
                        SubscriptionSyncState.last_error.label('last_error'),
                        func.coalesce(SubscriptionSyncState.pending_video_count, 0).label('pending_video_count'),
                    )
                    .outerjoin(
                        SubscriptionSyncState,
                        and_(
                            SubscriptionSyncState.subscription_id == Subscription.id,
                            SubscriptionSyncState.sync_mode == SyncMode.INCREMENTAL.value,
                        ),
                    )
                    .where(Subscription.id == subscription_id)
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            dto = SubscriptionDto.model_validate(row)
            dto.site = resolve_site_slug(dto.url)
            return dto

    def list_subscription_options(self, user_id: int) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.execute(
                select(Subscription.id, Subscription.name, Subscription.avatar)
                .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                    Subscription.is_deleted.is_(False),
                )
                .distinct()
                .order_by(Subscription.name.asc(), Subscription.id.asc()),
            ).all()

        return [
            {
                'subscription_id': subscription_id,
                'subscription_name': subscription_name,
                'subscription_avatar': subscription_avatar,
            }
            for subscription_id, subscription_name, subscription_avatar in rows
        ]


subscription_list_service = SubscriptionListService()
list_subscriptions = subscription_list_service.list_subscriptions
get_subscription_detail = subscription_list_service.get_subscription_detail
list_subscription_options = subscription_list_service.list_subscription_options
resolve_subscription_nsfw = resolve_subscription_nsfw_by_url
