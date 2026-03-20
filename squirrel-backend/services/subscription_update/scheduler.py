import logging
from typing import List, Optional

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from services import message_service, subscription_sync_state_service
from queues.direct_producer import direct_domain_producer
from utils.site_catalog import SiteCatalog
from .models import SubscriptionScheduleResult, SubscriptionUpdateRequest, UpdateTrigger, UpdateMode

logger = logging.getLogger()


class SubscriptionScheduler:
    """Subscription update scheduler."""

    def schedule_one(
        self,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        user_id: Optional[int] = None,
        force: bool = False,
        trace_id: Optional[str] = None
    ) -> SubscriptionScheduleResult:
        resolved_mode = self._resolve_mode(mode)
        domain = subscription_sync_state_service._resolve_site(url)
        if not domain or not SiteCatalog.is_site_enabled(domain=domain):
            logger.info(f"Skip scheduling subscription {subscription_id} because site is disabled: {domain}")
            return SubscriptionScheduleResult(subscription_id, None, "site_disabled")

        if not self._has_active_subscribers(subscription_id):
            logger.info(f"Skip scheduling subscription {subscription_id} because no active subscribers")
            return SubscriptionScheduleResult(subscription_id, None, "no_subscribers")

        sync_states = subscription_sync_state_service.ensure_sync_states(subscription_id, url)
        sync_state = sync_states[resolved_mode.value]
        sync_state = subscription_sync_state_service.recover_stale_sync_state(sync_state.id) or sync_state

        if sync_state.sync_status == 'running':
            return SubscriptionScheduleResult(subscription_id, sync_state.id, 'in_progress', sync_state.queue_token)
        if sync_state.sync_status == 'queued':
            return SubscriptionScheduleResult(subscription_id, sync_state.id, 'queued', sync_state.queue_token)

        if trigger == UpdateTrigger.SCHEDULED and subscription_sync_state_service.has_incremental_backpressure(sync_state):
            subscription_sync_state_service.defer_sync_state(
                sync_state.id,
                delay=subscription_sync_state_service.get_mode_interval(sync_state.sync_mode),
                error_message='queue_backpressure',
            )
            return SubscriptionScheduleResult(subscription_id, sync_state.id, 'deferred')

        queue_token = subscription_sync_state_service.build_queue_token()
        queued_state = subscription_sync_state_service.queue_sync_state(sync_state.id, queue_token)
        if not queued_state:
            return SubscriptionScheduleResult(subscription_id, sync_state.id if sync_state else None, 'failed')
        if queued_state.queue_token != queue_token:
            status = 'in_progress' if queued_state.sync_status == 'running' else 'queued'
            return SubscriptionScheduleResult(subscription_id, queued_state.id, status, queued_state.queue_token)
        if queued_state.sync_status != 'queued':
            return SubscriptionScheduleResult(subscription_id, queued_state.id, 'failed')

        content = {
            'subscription_id': subscription_id,
            'sync_state_id': queued_state.id,
            'mode': resolved_mode.value,
            'user_id': user_id,
            'force': force,
            'queue_token': queue_token,
            'trigger': trigger.value,
        }
        message = message_service.create_message(content, trace_id=trace_id)

        priority = self._resolve_priority(trigger, resolved_mode)
        try:
            direct_domain_producer.send_subscription_update(message.to_dict(), url, priority)
            logger.debug(f"Enqueued subscription {subscription_id} state={queued_state.id} priority={priority}")
            return SubscriptionScheduleResult(subscription_id, queued_state.id, 'queued', queue_token)
        except ValueError as e:
            subscription_sync_state_service.mark_sync_failed(queued_state.id, str(e))
            logger.error(f"Failed to enqueue subscription update: {e}, subscription_id={subscription_id}")
            return SubscriptionScheduleResult(subscription_id, queued_state.id, 'failed')

    def schedule_batch(
        self,
        subscription_ids: List[int],
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED
    ) -> tuple[int, int]:
        success_count = 0
        error_count = 0

        with get_session() as session:
            rows = session.execute(
                select(UserSubscription.subscription_id)
                .where(
                    UserSubscription.subscription_id.in_(subscription_ids),
                    UserSubscription.is_deleted.is_(False),
                )
            ).all()
            ids = [row[0] for row in rows]

        for subscription_id in ids:
            result = self.schedule_one(subscription_id, self._get_subscription_url(subscription_id), trigger)
            if result.status == 'queued':
                success_count += 1
            elif result.status == 'failed':
                error_count += 1

        return success_count, error_count

    def enqueue_all_active(
        self,
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED,
        mode: UpdateMode = UpdateMode.INCREMENTAL
    ) -> tuple[int, int]:
        resolved_mode = self._resolve_mode(mode)
        due_states = subscription_sync_state_service.list_due_sync_states(resolved_mode.value)
        if not due_states:
            logger.info(f"No due subscription sync states (mode={resolved_mode.value})")
            return 0, 0

        success_count = 0
        error_count = 0
        for sync_state, url in due_states:
            result = self.schedule_one(
                subscription_id=sync_state.subscription_id,
                url=url,
                trigger=trigger,
                mode=resolved_mode,
            )
            if result.status == 'queued':
                success_count += 1
            elif result.status == 'failed':
                error_count += 1
        logger.info(f"Enqueue completed: success={success_count}, failed={error_count}, mode={resolved_mode.value}")
        return success_count, error_count

    @staticmethod
    def _resolve_priority(trigger: UpdateTrigger, mode: UpdateMode) -> str:
        if trigger == UpdateTrigger.MANUAL:
            return 'manual'
        if mode == UpdateMode.FULL:
            return 'full'
        return 'incr'

    @staticmethod
    def _resolve_mode(mode: UpdateMode) -> UpdateMode:
        if mode == UpdateMode.FULL:
            return UpdateMode.FULL
        return UpdateMode.INCREMENTAL

    @staticmethod
    def _has_active_subscribers(subscription_id: int) -> bool:
        with get_session() as session:
            row = session.execute(
                select(UserSubscription.id).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ).limit(1)
            ).first()
            return row is not None

    @staticmethod
    def _get_subscription_url(subscription_id: int) -> str:
        from services import subscription_service

        subscription = subscription_service.get_subscription_by_id(subscription_id)
        return subscription.url if subscription and subscription.url else ''


scheduler = SubscriptionScheduler()
