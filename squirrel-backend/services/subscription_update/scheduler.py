import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from models.subscription import Subscription
from services.crawl_tasks.task_types import resolve_subscription_sync_task_type
from services import outbox_event_service, subscription_sync_state_service
from services.crawl_tasks import service as crawl_task_service
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncPhase, SyncRunContext, SyncRunStatus, create_run
from utils.site_catalog import SiteCatalog
from utils.trace import generate_trace_id, get_trace_id
from .models import (
    SubscriptionDirectRunResult,
    SubscriptionScheduleResult,
    SubscriptionUpdateRequest,
    SubscriptionUpdateResult,
    UpdateTrigger,
    UpdateMode,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _DueSyncTarget:
    subscription_id: int
    url: str
    sync_state_id: Optional[int] = None
    site: Optional[str] = None


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

        event_type = 'full_sync_due' if resolved_mode == UpdateMode.FULL else 'incremental_sync_due'
        event = outbox_event_service.publish_event(
            event_type=event_type,
            event_key=self._build_schedule_event_key(event_type=event_type, run_id=run_context.run_id),
            aggregate_type='subscription',
            aggregate_id=str(subscription_id),
            payload={
                'subscription_id': subscription_id,
                'mode': resolved_mode.value,
                'trigger': trigger.value,
                'url': url,
                'site': domain,
                'user_id': user_id,
                'force': force,
                'trace_id': trace_id,
                'run_id': run_context.run_id,
            },
            priority=self._resolve_priority(trigger, resolved_mode),
            available_at=datetime.now(),
        )
        return SubscriptionScheduleResult(
            subscription_id=subscription_id,
            sync_state_id=None,
            status='queued',
            request_id=str(event.id),
            run_id=run_context.run_id,
        )

    def run_one_inline(
        self,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        user_id: Optional[int] = None,
        force: bool = False,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> SubscriptionDirectRunResult:
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
            result = SubscriptionUpdateResult(
                subscription_id=subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
                skipped_reason='site_disabled',
            )
            return SubscriptionDirectRunResult(
                subscription_id,
                None,
                'site_disabled',
                run_id=run_context.run_id,
                result=result,
            )

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
            result = SubscriptionUpdateResult(
                subscription_id=subscription_id,
                success=True,
                videos_found=0,
                videos_enqueued=0,
                skipped_reason='no_subscribers',
            )
            return SubscriptionDirectRunResult(
                subscription_id,
                None,
                'no_subscribers',
                run_id=run_context.run_id,
                result=result,
            )

        sync_state, state_status = subscription_sync_state_service.prepare_sync_state_for_enqueue(
            subscription_id,
            url,
            resolved_mode.value,
            scheduled=False,
        )
        if not sync_state:
            result = SubscriptionUpdateResult(
                subscription_id=subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message='sync_state_prepare_failed',
            )
            return SubscriptionDirectRunResult(subscription_id, None, 'failed', result=result)
        if state_status in {'in_progress', 'queued'}:
            return SubscriptionDirectRunResult(subscription_id, sync_state.id, state_status)

        run_context, emit_run_created = self._build_run_context(
            subscription_id=subscription_id,
            sync_state_id=sync_state.id,
            site=domain,
            sync_mode=resolved_mode.value,
            trigger=trigger.value,
            trace_id=trace_id,
            run_id=run_id,
        )
        request_id = f'direct:{run_context.run_id}'
        if emit_run_created:
            append_event(SyncEventInput(
                stream_id=run_context.run_id,
                subscription_id=subscription_id,
                sync_state_id=sync_state.id,
                site=domain,
                sync_mode=resolved_mode.value,
                trigger=trigger.value,
                request_id=request_id,
                trace_id=trace_id,
                event_type=SyncEventType.RUN_CREATED,
                event_phase=SyncPhase.INIT,
                event_status=SyncRunStatus.CREATED,
                payload={'pending_video_count': sync_state.pending_video_count},
                occurred_at=run_context.created_at,
            ))

        queue_token = subscription_sync_state_service.build_queue_token()
        queued_state = subscription_sync_state_service.queue_sync_state(sync_state.id, queue_token)
        if not queued_state or queued_state.queue_token != queue_token or queued_state.sync_status != 'queued':
            result = SubscriptionUpdateResult(
                subscription_id=subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message='sync_state_queue_failed',
            )
            return SubscriptionDirectRunResult(
                subscription_id=subscription_id,
                sync_state_id=sync_state.id,
                status='failed',
                request_id=request_id,
                run_id=run_context.run_id,
                result=result,
            )

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
                'direct': True,
            },
        ))

        from services.crawl_executors.subscription_sync_executor import execute_subscription_sync_payload

        try:
            result = execute_subscription_sync_payload({
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
                'request_id': request_id,
                'inline_video_extraction': True,
            })
        except Exception as exc:
            subscription_sync_state_service.mark_sync_failed(
                queued_state.id,
                str(exc),
                run_id=run_context.run_id,
                request_id=request_id,
                trace_id=trace_id,
                error_type=type(exc).__name__,
                trigger=trigger.value,
            )
            result = SubscriptionUpdateResult(
                subscription_id=subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(exc),
            )

        return SubscriptionDirectRunResult(
            subscription_id=subscription_id,
            sync_state_id=queued_state.id,
            status='success' if result.success else 'failed',
            request_id=request_id,
            run_id=run_context.run_id,
            result=result,
        )

    def _schedule_one_direct(
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
            task_type=resolve_subscription_sync_task_type(resolved_mode.value),
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
        targets = (
            _DueSyncTarget(subscription_id=subscription_id, url=url)
            for subscription_id, url in self._list_due_active_subscriptions(resolved_mode)
        )
        return self._dispatch_due_targets(
            targets=targets,
            mode=resolved_mode,
            action_name='enqueue',
            action=lambda target: self._schedule_due_target(target=target, trigger=trigger, mode=resolved_mode),
        )

    def enqueue_due_states(
        self,
        trigger: UpdateTrigger = UpdateTrigger.SCHEDULED,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        *,
        now: Optional[datetime] = None,
        limit: int = subscription_sync_state_service.SYNC_BATCH_SIZE,
    ) -> tuple[int, int]:
        resolved_mode = self._resolve_mode(mode)
        current_time = now or datetime.now()
        targets = (
            _DueSyncTarget(
                subscription_id=sync_state.subscription_id,
                sync_state_id=sync_state.id,
                site=sync_state.site,
                url=url,
            )
            for sync_state, url in subscription_sync_state_service.list_due_sync_states(
                resolved_mode.value,
                limit=limit,
                now=current_time,
            )
        )
        return self._dispatch_due_targets(
            targets=targets,
            mode=resolved_mode,
            action_name='emit',
            action=lambda target: self._emit_due_sync_event(
                target=target,
                trigger=trigger,
                mode=resolved_mode,
                now=current_time,
            ),
        )

    def _dispatch_due_targets(
        self,
        *,
        targets: Iterable[_DueSyncTarget],
        mode: UpdateMode,
        action_name: str,
        action: Callable[[_DueSyncTarget], str],
    ) -> tuple[int, int]:
        success_count = 0
        error_count = 0

        for target in targets:
            try:
                action_result = action(target)
                if action_result == 'success':
                    success_count += 1
                elif action_result == 'failed':
                    error_count += 1
            except Exception:
                error_count += 1
                logger.exception(
                    'Failed to %s due sync target subscription_id=%s sync_state_id=%s mode=%s',
                    action_name,
                    target.subscription_id,
                    target.sync_state_id,
                    mode.value,
                )

        logger.info(
            'Due sync %s completed: success=%s failed=%s mode=%s',
            action_name,
            success_count,
            error_count,
            mode.value,
        )
        return success_count, error_count

    def _schedule_due_target(
        self,
        *,
        target: _DueSyncTarget,
        trigger: UpdateTrigger,
        mode: UpdateMode,
    ) -> str:
        result = self.schedule_one(
            subscription_id=target.subscription_id,
            url=target.url,
            trigger=trigger,
            mode=mode,
        )
        if result.status == 'queued':
            return 'success'
        if result.status == 'failed':
            return 'failed'
        return 'skipped'

    def _emit_due_sync_event(
        self,
        *,
        target: _DueSyncTarget,
        trigger: UpdateTrigger,
        mode: UpdateMode,
        now: datetime,
    ) -> str:
        if target.sync_state_id is None:
            return 'skipped'

        event_type = 'full_sync_due' if mode == UpdateMode.FULL else 'incremental_sync_due'
        trace_id = self._resolve_trace_id(None)
        outbox_event_service.publish_event(
            event_type=event_type,
            event_key=self._build_due_event_key(target.sync_state_id, event_type, now),
            aggregate_type='subscription_sync_state',
            aggregate_id=str(target.sync_state_id),
            payload={
                'subscription_id': target.subscription_id,
                'sync_state_id': target.sync_state_id,
                'site': target.site,
                'mode': mode.value,
                'trigger': trigger.value,
                'url': target.url,
                'trace_id': trace_id,
            },
            priority='low' if mode == UpdateMode.FULL else 'normal',
            available_at=now,
        )
        return 'success'

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
    def _build_due_event_key(sync_state_id: int, event_type: str, now: datetime) -> str:
        bucket = now.replace(second=0, microsecond=0).isoformat()
        return f'{event_type}:{sync_state_id}:{bucket}'

    @staticmethod
    def _build_schedule_event_key(*, event_type: str, run_id: str) -> str:
        return f'{event_type}:{run_id}:{uuid4().hex}'

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
