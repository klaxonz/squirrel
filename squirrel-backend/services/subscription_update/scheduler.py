import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from services import subscription_sync_state_service
from services.crawl_tasks import service as crawl_task_service
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncPhase, SyncRunContext, SyncRunStatus, create_run
from utils.site_catalog import SiteCatalog
from utils.trace import generate_trace_id, get_trace_id
from .models import SubscriptionScheduleResult, SubscriptionUpdateRequest, UpdateTrigger, UpdateMode

logger = logging.getLogger()


class SubscriptionScheduler:
    """Subscription update scheduler."""

    @staticmethod
    def _resolve_trace_id(trace_id: Optional[str]) -> str:
        return trace_id or get_trace_id() or generate_trace_id()

    @staticmethod
    def _build_run_context(
        *,
        subscription_id: int,
        sync_state_id: Optional[int],
        site: Optional[str],
        sync_mode: str,
        trigger: str,
        trace_id: str,
        run_id: Optional[str],
    ) -> tuple[SyncRunContext, bool]:
        if run_id:
            now = datetime.now()
            return (
                SyncRunContext(
                    run_id=run_id,
                    stream_id=run_id,
                    subscription_id=subscription_id,
                    sync_state_id=sync_state_id,
                    site=(site or '').strip(),
                    sync_mode=sync_mode,
                    trigger=trigger,
                    request_id=None,
                    trace_id=trace_id,
                    created_at=now,
                ),
                False,
            )
        return (
            create_run(
                subscription_id=subscription_id,
                sync_state_id=sync_state_id,
                site=site,
                sync_mode=sync_mode,
                trigger=trigger,
                trace_id=trace_id,
            ),
            True,
        )

    def schedule_one(
        self,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        user_id: Optional[int] = None,
        force: bool = False,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> SubscriptionScheduleResult:
        trace_id = self._resolve_trace_id(trace_id)
        resolved_mode = self._resolve_mode(mode)
        domain = subscription_sync_state_service._resolve_site(url)
        if not domain or not SiteCatalog.is_site_enabled(domain=domain):
            run_context, emit_run_created = self._build_run_context(
                subscription_id=subscription_id,
                sync_state_id=None,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                run_id=run_id,
            )
            if emit_run_created:
                append_event(SyncEventInput(
                    stream_id=run_context.run_id,
                    subscription_id=subscription_id,
                    sync_state_id=None,
                    site=domain,
                    sync_mode=resolved_mode.value,
                    trigger=trigger.value,
                    trace_id=trace_id,
                    event_type=SyncEventType.RUN_CREATED,
                    event_phase=SyncPhase.INIT,
                    event_status=SyncRunStatus.CREATED,
                    payload={'pending_video_count': 0},
                    occurred_at=run_context.created_at,
                ))
            append_event(SyncEventInput(
                stream_id=run_context.run_id,
                subscription_id=subscription_id,
                sync_state_id=None,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                event_type=SyncEventType.DEFERRED,
                event_phase=SyncPhase.DEFERRED,
                event_status=SyncRunStatus.DEFERRED,
                payload={'reason': 'site_disabled', 'error_message': 'site_disabled'},
            ))
            logger.info(f"Skip scheduling subscription {subscription_id} because site is disabled: {domain}")
            return SubscriptionScheduleResult(subscription_id, None, "site_disabled", run_id=run_context.run_id)

        if not self._has_active_subscribers(subscription_id):
            run_context, emit_run_created = self._build_run_context(
                subscription_id=subscription_id,
                sync_state_id=None,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                run_id=run_id,
            )
            if emit_run_created:
                append_event(SyncEventInput(
                    stream_id=run_context.run_id,
                    subscription_id=subscription_id,
                    sync_state_id=None,
                    site=domain,
                    sync_mode=resolved_mode.value,
                    trigger=trigger.value,
                    trace_id=trace_id,
                    event_type=SyncEventType.RUN_CREATED,
                    event_phase=SyncPhase.INIT,
                    event_status=SyncRunStatus.CREATED,
                    payload={'pending_video_count': 0},
                    occurred_at=run_context.created_at,
                ))
            append_event(SyncEventInput(
                stream_id=run_context.run_id,
                subscription_id=subscription_id,
                sync_state_id=None,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                event_type=SyncEventType.DEFERRED,
                event_phase=SyncPhase.DEFERRED,
                event_status=SyncRunStatus.DEFERRED,
                payload={'reason': 'no_subscribers', 'error_message': 'no_subscribers'},
            ))
            logger.info(f"Skip scheduling subscription {subscription_id} because no active subscribers")
            return SubscriptionScheduleResult(subscription_id, None, "no_subscribers", run_id=run_context.run_id)

        sync_state, state_status = subscription_sync_state_service.prepare_sync_state_for_enqueue(
            subscription_id,
            url,
            resolved_mode.value,
            scheduled=trigger == UpdateTrigger.SCHEDULED,
        )
        if not sync_state:
            return SubscriptionScheduleResult(subscription_id=subscription_id, sync_state_id=None, status='failed')

        if state_status == 'in_progress':
            return SubscriptionScheduleResult(
                subscription_id=subscription_id,
                sync_state_id=sync_state.id,
                status='in_progress',
            )
        if state_status == 'queued':
            return SubscriptionScheduleResult(
                subscription_id=subscription_id,
                sync_state_id=sync_state.id,
                status='queued',
            )

        run_context, emit_run_created = self._build_run_context(
            subscription_id=subscription_id,
            sync_state_id=sync_state.id,
            site=domain,
            sync_mode=resolved_mode.value,
            trigger=trigger.value,
            trace_id=trace_id,
            run_id=run_id,
        )
        if emit_run_created:
            append_event(SyncEventInput(
                stream_id=run_context.run_id,
                subscription_id=subscription_id,
                sync_state_id=sync_state.id,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                event_type=SyncEventType.RUN_CREATED,
                event_phase=SyncPhase.INIT,
                event_status=SyncRunStatus.CREATED,
                payload={'pending_video_count': sync_state.pending_video_count},
                occurred_at=run_context.created_at,
            ))
        if state_status == 'deferred':
            append_event(SyncEventInput(
                stream_id=run_context.run_id,
                subscription_id=subscription_id,
                sync_state_id=sync_state.id,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                event_type=SyncEventType.DEFERRED,
                event_phase=SyncPhase.DEFERRED,
                event_status=SyncRunStatus.DEFERRED,
                payload={
                    'reason': 'queue_backpressure',
                    'pending_video_count': sync_state.pending_video_count,
                    'next_sync_at': sync_state.next_sync_at,
                    'error_message': 'queue_backpressure',
                },
            ))
            return SubscriptionScheduleResult(
                subscription_id=subscription_id,
                sync_state_id=sync_state.id,
                status='deferred',
                run_id=run_context.run_id,
            )

        queue_token = subscription_sync_state_service.build_queue_token()
        queued_state = subscription_sync_state_service.queue_sync_state(sync_state.id, queue_token)
        if not queued_state:
            return SubscriptionScheduleResult(
                subscription_id=subscription_id,
                sync_state_id=sync_state.id if sync_state else None,
                status='failed',
            )
        if queued_state.queue_token != queue_token:
            status = 'in_progress' if queued_state.sync_status == 'running' else 'queued'
            append_event(SyncEventInput(
                stream_id=run_context.run_id,
                subscription_id=subscription_id,
                sync_state_id=queued_state.id,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                event_type=SyncEventType.DEFERRED,
                event_phase=SyncPhase.DEFERRED,
                event_status=SyncRunStatus.DEFERRED,
                payload={'reason': 'queue_state_mismatch'},
            ))
            return SubscriptionScheduleResult(subscription_id=subscription_id, sync_state_id=queued_state.id, status=status)
        if queued_state.sync_status != 'queued':
            append_event(SyncEventInput(
                stream_id=run_context.run_id,
                subscription_id=subscription_id,
                sync_state_id=queued_state.id,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                trace_id=trace_id,
                event_type=SyncEventType.DEFERRED,
                event_phase=SyncPhase.DEFERRED,
                event_status=SyncRunStatus.DEFERRED,
                payload={'reason': 'queue_state_invalid'},
            ))
            return SubscriptionScheduleResult(subscription_id=subscription_id, sync_state_id=queued_state.id, status='failed')

        priority = self._resolve_priority(trigger, resolved_mode)
        task_payload = {
            'subscription_id': subscription_id,
            'url': url,
            'sync_state_id': queued_state.id,
            'mode': resolved_mode.value,
            'user_id': user_id,
            'force': force,
            'queue_token': queue_token,
            'trigger': trigger.value,
            'run_id': run_context.run_id,
            'trace_id': trace_id,
        }
        source_type = 'manual' if trigger == UpdateTrigger.MANUAL else 'scheduled'
        _, task = crawl_task_service.create_job_with_task(
            job_type='subscription_sync',
            source_type=source_type,
            site=domain,
            subscription_id=subscription_id,
            priority=priority,
            task_type='subscription_sync',
            payload=task_payload,
            trace_id=trace_id,
        )
        request_id = str(task.id)
        append_event(SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=subscription_id,
            sync_state_id=queued_state.id,
            site=domain,
            sync_mode=resolved_mode.value,
            trigger=trigger.value,
            request_id=request_id,
            trace_id=trace_id,
            event_type=SyncEventType.QUEUED,
            event_phase=SyncPhase.QUEUED,
            event_status=SyncRunStatus.QUEUED,
            payload={
                'queue_token': queue_token,
                'queued_at': queued_state.queued_at,
                'pending_video_count': queued_state.pending_video_count,
            },
        ))
        logger.debug(
            "Scheduled subscription sync into crawl task store subscription_id=%s sync_state_id=%s task_id=%s priority=%s",
            subscription_id,
            queued_state.id,
            task.id,
            priority,
        )
        return SubscriptionScheduleResult(
            subscription_id=subscription_id,
            sync_state_id=queued_state.id,
            status='queued',
            request_id=request_id,
            run_id=run_context.run_id,
        )

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
        success_count = 0
        error_count = 0

        for subscription_id, url in self._list_due_active_subscriptions(resolved_mode):
            result = self.schedule_one(
                subscription_id=subscription_id,
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
    def _list_due_active_subscriptions(mode: UpdateMode) -> list[tuple[int, str]]:
        now = datetime.now()

        with get_session() as session:
            rows = session.execute(
                select(Subscription.id, Subscription.url)
                .where(
                    Subscription.is_deleted.is_(False),
                    Subscription.url.is_not(None),
                )
                .where(
                    select(UserSubscription.id)
                    .where(
                        UserSubscription.subscription_id == Subscription.id,
                        UserSubscription.is_deleted.is_(False),
                    )
                    .exists()
                )
                .order_by(Subscription.id.asc())
            ).all()

        due_subscriptions: list[tuple[int, str]] = []
        for subscription_id, url in rows:
            sync_state = subscription_sync_state_service.get_sync_state(subscription_id, mode.value)
            if sync_state is None:
                due_subscriptions.append((subscription_id, url))
                continue

            sync_status = getattr(sync_state, 'sync_status', None)
            if sync_status in {'queued', 'running'}:
                continue

            next_sync_at = getattr(sync_state, 'next_sync_at', None)
            if next_sync_at is None or next_sync_at <= now:
                due_subscriptions.append((subscription_id, url))

        return due_subscriptions

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
