from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
from domains.subscription.application.services.core.crud import get_subscription_by_id
from domains.subscription.application.services.core.update.command_events import (
    SubscriptionSyncCommandEventPublisher,
    subscription_sync_command_event_publisher,
)
from domains.subscription.application.services.core.update.command_payloads import (
    build_command,
    build_task_payload,
    resolve_priority,
)
from domains.subscription.application.services.core.update.command_preflight import resolve_preflight_result
from domains.subscription.application.services.core.update.models import (
    SubscriptionDirectRunResult,
    SubscriptionScheduleResult,
    SubscriptionUpdateRequest,
    SubscriptionUpdateResult,
    UpdateMode,
    UpdateTrigger,
)
from domains.subscription.application.services.core.update.queueing import SubscriptionSyncQueuePlanner
from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.application.services.crawl.tasks.task_types import resolve_subscription_sync_task_type
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session
from infrastructure.site_catalog.url import resolve_site

logger = logging.getLogger(__name__)

FULL_BACKFILL_RETRY_COOLDOWN = timedelta(hours=6)
FULL_BACKFILL_STALE_AFTER = timedelta(days=3)


@dataclass(frozen=True)
class SubscriptionSyncTarget:
    subscription_id: int
    url: str
    sync_state_id: int | None = None
    site: str | None = None


@dataclass(frozen=True)
class SubscriptionSyncRecoveryResult:
    video_states: int
    videos: int
    drained_completed: int
    drained_failed: int
    queued_recovered: int
    running_recovered: int


def should_schedule_total_video_backfill(
    sync_mode: str,
    local_total_videos: int | None,
    observed_total_available: int | None,
    full_sync_status: str | None,
    full_last_success_at: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    current_time = now or datetime.now()

    if sync_mode == SyncMode.FULL.value:
        return False
    if full_sync_status in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
        return False

    local_total = max(int(local_total_videos or 0), 0)
    observed_total = max(int(observed_total_available), 0) if observed_total_available is not None else None

    if full_last_success_at is None:
        return True

    if local_total <= 0 and full_last_success_at <= current_time - FULL_BACKFILL_RETRY_COOLDOWN:
        return True

    if observed_total is not None and observed_total > local_total:
        return full_last_success_at <= current_time - FULL_BACKFILL_RETRY_COOLDOWN

    return full_last_success_at <= current_time - FULL_BACKFILL_STALE_AFTER


class SubscriptionSyncLifecycle:
    def __init__(
        self,
        session_factory=None,
        sync_state_service=None,
        crawl_tasks=None,
        event_publisher: SubscriptionSyncCommandEventPublisher | None = None,
    ):
        self.session_factory = session_factory or get_session
        self._sync_state_service = sync_state_service or subscription_sync_state_service
        self._crawl_tasks = crawl_tasks or crawl_task_service
        self._event_publisher = event_publisher or subscription_sync_command_event_publisher
        self._queue_planner = SubscriptionSyncQueuePlanner(self._sync_state_service, self._event_publisher)

    def request_sync(
        self,
        *,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        user_id: int | None = None,
        force: bool = False,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> SubscriptionScheduleResult:
        command = build_command(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=user_id,
            force=force,
            trace_id=trace_id,
            run_id=run_id,
        )
        domain = resolve_site(command.url)
        preflight = resolve_preflight_result(
            command,
            domain,
            direct=False,
            event_publisher=self._event_publisher,
            has_active_subscribers=self._has_active_subscribers,
        )
        if preflight is not None:
            return preflight

        queued = self._queue_planner.queue_sync_state(
            command,
            domain=domain,
            scheduled=command.trigger == UpdateTrigger.SCHEDULED,
        )
        if queued.status != 'ready':
            return SubscriptionScheduleResult(
                subscription_id=command.subscription_id,
                sync_state_id=queued.sync_state_id,
                status=queued.status,
                run_id=queued.run_context.run_id if queued.run_context else command.run_id,
            )

        task_payload = build_task_payload(
            command,
            queued.sync_state_id,
            queued.queue_token,
            request_id=None,
            run_id=queued.run_context.run_id,
        )
        _, task = self._crawl_tasks.create_job_with_task(
            job_type='subscription_sync',
            source_type='manual' if command.trigger == UpdateTrigger.MANUAL else 'scheduled',
            site=domain,
            subscription_id=command.subscription_id,
            priority=resolve_priority(command.trigger, command.mode),
            task_type=resolve_subscription_sync_task_type(command.mode.value),
            payload=task_payload,
            trace_id=command.trace_id,
        )
        request_id = str(task.id)
        task.payload['request_id'] = request_id
        self._set_task_request_id(task.id, request_id)

        logger.debug(
            'Queued subscription sync task subscription_id=%s sync_state_id=%s task_id=%s priority=%s',
            command.subscription_id,
            queued.sync_state_id,
            task.id,
            resolve_priority(command.trigger, command.mode),
        )
        return SubscriptionScheduleResult(
            subscription_id=command.subscription_id,
            sync_state_id=queued.sync_state_id,
            status='queued',
            request_id=request_id,
            run_id=queued.run_context.run_id,
        )

    def run_inline_sync(
        self,
        *,
        subscription_id: int,
        url: str,
        trigger: UpdateTrigger = UpdateTrigger.MANUAL,
        mode: UpdateMode = UpdateMode.INCREMENTAL,
        user_id: int | None = None,
        force: bool = False,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> SubscriptionDirectRunResult:
        command = build_command(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=mode,
            user_id=user_id,
            force=force,
            trace_id=trace_id,
            run_id=run_id,
        )
        domain = resolve_site(command.url)
        preflight = resolve_preflight_result(
            command,
            domain,
            direct=True,
            event_publisher=self._event_publisher,
            has_active_subscribers=self._has_active_subscribers,
        )
        if isinstance(preflight, SubscriptionDirectRunResult):
            return preflight

        queued = self._queue_planner.queue_sync_state(command, domain=domain, scheduled=False)
        if queued.status != 'ready':
            return SubscriptionDirectRunResult(
                subscription_id=command.subscription_id,
                sync_state_id=queued.sync_state_id,
                status=queued.status,
                run_id=queued.run_context.run_id if queued.run_context else command.run_id,
            )

        request_id = f'direct:{queued.run_context.run_id}'

        from domains.subscription.application.services.crawl.executors.subscription_sync_executor import (
            execute_subscription_sync_payload,
        )

        try:
            sync_result = execute_subscription_sync_payload({
                **build_task_payload(
                    command,
                    queued.sync_state_id,
                    queued.queue_token,
                    request_id=request_id,
                    run_id=queued.run_context.run_id,
                ),
                'inline_video_extraction': True,
            })
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            self._sync_state_service.mark_sync_failed(
                queued.sync_state_id,
                str(exc),
                error_type=type(exc).__name__,
            )
            sync_result = SubscriptionUpdateResult(
                subscription_id=command.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(exc),
            )

        return SubscriptionDirectRunResult(
            subscription_id=command.subscription_id,
            sync_state_id=queued.sync_state_id,
            status='success' if sync_result.success else 'failed',
            request_id=request_id,
            run_id=queued.run_context.run_id,
            result=sync_result,
        )

    def claim_sync(
        self,
        sync_state_id: int,
        queue_token: str,
        *,
        run_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        trigger: str | None = None,
    ):
        return self._sync_state_service.claim_sync_state(
            sync_state_id,
            queue_token,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
        )

    def list_due_sync_targets(
        self,
        mode: UpdateMode,
        *,
        now: datetime | None = None,
        limit: int | None = None,
    ) -> list[SubscriptionSyncTarget]:
        resolved_mode = UpdateMode.FULL if mode == UpdateMode.FULL else UpdateMode.INCREMENTAL
        current_time = now or datetime.now()
        row_limit = self._sync_state_service.SYNC_BATCH_SIZE if limit is None else limit
        return [
            SubscriptionSyncTarget(
                subscription_id=sync_state.subscription_id,
                sync_state_id=sync_state.id,
                site=sync_state.site,
                url=url,
            )
            for sync_state, url in self._sync_state_service.list_due_sync_states(
                resolved_mode.value,
                limit=row_limit,
                now=current_time,
            )
        ]

    def ensure_subscription_syncs(self, subscription_id: int, url: str | None) -> None:
        self._sync_state_service.ensure_sync_states(subscription_id, url)

    def deactivate_subscription_syncs(self, subscription_id: int, *, reason: str) -> None:
        self._sync_state_service.deactivate_sync_states(subscription_id, reason=reason)

    def skip_sync(self, request: SubscriptionUpdateRequest, *, reason: str) -> None:
        if not request.sync_state_id:
            return
        self._sync_state_service.mark_sync_skipped(
            request.sync_state_id,
            reason=reason,
        )

    def fail_sync(self, request: SubscriptionUpdateRequest, error: Exception | str) -> None:
        if not request.sync_state_id:
            return
        self._sync_state_service.mark_sync_failed(
            request.sync_state_id,
            str(error),
            error_type=type(error).__name__ if isinstance(error, Exception) else None,
        )

    def complete_sync(self, request: SubscriptionUpdateRequest, result: SubscriptionUpdateResult) -> None:
        if not request.sync_state_id:
            return

        if request.mode == UpdateMode.FULL and result.has_more:
            self._sync_state_service.continue_full_sync_batch(
                request.sync_state_id,
                cursor_payload=result.cursor_payload,
                latest_video_url=result.latest_video_url,
                videos_found=result.videos_found,
            )
            self._continue_full_sync(request)
            return

        self._sync_state_service.mark_sync_success(
            request.sync_state_id,
            cursor_payload=result.cursor_payload,
            latest_video_url=result.latest_video_url,
            videos_found=result.videos_found,
        )

    def record_gap_observation(
        self,
        request: SubscriptionUpdateRequest,
        result: SubscriptionUpdateResult,
    ) -> None:
        if request.mode != UpdateMode.INCREMENTAL or not request.sync_state_id:
            return

        subscription = get_subscription_by_id(request.subscription_id)
        local_total = getattr(subscription, 'total_videos', None) if subscription else None
        summary = self._sync_state_service.record_gap_observation(
            sync_state_id=request.sync_state_id,
            head_sample_urls=result.head_sample_urls,
            anchor_found=result.anchor_found,
            cursor_invalid=bool(result.cursor_invalid),
            cursor_loop_detected=bool(result.cursor_loop_detected),
            total_available=result.total_available,
            local_total=local_total,
        )
        if not summary['should_request_full']:
            return

        site = str(summary['site'] or '').strip()
        if not self._can_request_full_sync(site):
            return

        try:
            self.request_sync(
                subscription_id=request.subscription_id,
                url=request.url,
                trigger=request.trigger,
                mode=UpdateMode.FULL,
                trace_id=request.trace_id,
            )
            logger.info(
                'Gap detection enqueued full backfill subscription_id=%s site=%s sync_state_id=%s gap_score=%s',
                request.subscription_id,
                site,
                summary['sync_state_id'],
                summary['gap_suspicion_score'],
            )
        except Exception:  # gap backfill boundary — never fail the observation path
            logger.exception(
                'Failed to enqueue full backfill from gap detection subscription_id=%s sync_state_id=%s',
                request.subscription_id,
                summary['sync_state_id'],
            )

    def request_total_video_backfill_if_needed(
        self,
        request: SubscriptionUpdateRequest,
        result: SubscriptionUpdateResult,
    ) -> None:
        if request.inline_video_extraction:
            return

        subscription = get_subscription_by_id(request.subscription_id)
        if not subscription:
            return

        full_state = self._sync_state_service.get_sync_state(request.subscription_id, SyncMode.FULL.value)
        if not should_schedule_total_video_backfill(
            request.mode.value,
            subscription.total_videos,
            result.total_available,
            full_state.sync_status if full_state else None,
            full_state.last_success_at if full_state else None,
        ):
            return

        scheduled = self.request_sync(
            subscription_id=request.subscription_id,
            url=request.url,
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.FULL,
            trace_id=request.trace_id,
        )
        logger.info(
            'Scheduled full sync to backfill total videos: subscription_id=%s, status=%s',
            request.subscription_id,
            scheduled.status,
        )

    def record_task_retry_transition(
        self,
        sync_state_id: int,
        queue_token: str | None,
        *,
        now: datetime,
        retryable: bool,
        error_message: str | None,
        run_id: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        trigger: str | None = None,
    ) -> None:
        self._sync_state_service.reconcile_task_retry_state(
            sync_state_id,
            queue_token,
            now=now,
            retryable=retryable,
            error_message=error_message,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
        )

    def record_video_extraction_enqueued(self, sync_state_id: int | None) -> None:
        self._sync_state_service.increment_pending_video_count(sync_state_id, 1)

    def record_video_extraction_dispatch_failed(self, sync_state_id: int | None) -> None:
        self._sync_state_service.decrement_pending_video_count(
            sync_state_id,
            allow_completion=False,
        )

    def record_video_extraction_finished(self, sync_state_id: int | None, *, succeeded: bool) -> None:
        self._sync_state_service.decrement_pending_video_count(
            sync_state_id,
            allow_completion=succeeded,
        )

    def recover(self) -> SubscriptionSyncRecoveryResult:
        video_result = self._sync_state_service.reconcile_pending_video_counts()
        drained_result = self._sync_state_service.reconcile_terminal_drained_sync_states()
        queued_result = self._sync_state_service.recover_stale_queued_sync_states()
        running_result = self._sync_state_service.recover_stale_running_sync_states()
        return SubscriptionSyncRecoveryResult(
            video_states=video_result['states'],
            videos=video_result['videos'],
            drained_completed=drained_result['completed'],
            drained_failed=drained_result['failed'],
            queued_recovered=queued_result['recovered'],
            running_recovered=running_result['recovered'],
        )

    def recover_on_startup(self) -> dict[str, int]:
        return self._sync_state_service.recover_stale_sync_states_on_startup()

    def _continue_full_sync(self, request: SubscriptionUpdateRequest) -> None:
        if request.inline_video_extraction:
            continuation_result = self.run_inline_sync(
                subscription_id=request.subscription_id,
                url=request.url,
                trigger=request.trigger,
                mode=request.mode,
                user_id=request.user_id,
                force=request.force,
                trace_id=request.trace_id,
                run_id=request.run_id,
            )
            expected_status = 'success'
        else:
            continuation_result = self.request_sync(
                subscription_id=request.subscription_id,
                url=request.url,
                trigger=request.trigger,
                mode=request.mode,
                user_id=request.user_id,
                force=request.force,
                trace_id=request.trace_id,
                run_id=request.run_id,
            )
            expected_status = 'queued'

        if continuation_result.status != expected_status:
            raise ValueError(
                f'Failed to continue subscription sync: subscription_id={request.subscription_id}, '
                f'status={continuation_result.status}',
            )

    def _can_request_full_sync(self, site: str) -> bool:
        global_limit = max(1, int(settings.FULL_SYNC_MAX_INFLIGHT))
        site_limit = max(1, int(settings.FULL_SYNC_SITE_MAX_INFLIGHT))

        with self.session_factory() as session:
            global_inflight = int(session.execute(
                select(func.count(SubscriptionSyncState.id)).where(
                    SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                    SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
                ),
            ).scalar_one() or 0)
            if global_inflight >= global_limit:
                return False

            if site:
                site_inflight = int(session.execute(
                    select(func.count(SubscriptionSyncState.id)).where(
                        SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                        SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
                        SubscriptionSyncState.site == site,
                    ),
                ).scalar_one() or 0)
                if site_inflight >= site_limit:
                    return False

        return True

    def _set_task_request_id(self, task_id: int, request_id: str) -> None:
        from domains.subscription.domain.models.crawl_task import CrawlTask

        with self.session_factory() as session:
            task = session.get(CrawlTask, task_id)
            if task is None:
                return
            task.payload = {**(task.payload or {}), 'request_id': request_id}

    def _has_active_subscribers(self, subscription_id: int) -> bool:
        with self.session_factory() as session:
            row = session.execute(
                select(UserSubscription.id).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ).limit(1),
            ).first()
            return row is not None


subscription_sync_lifecycle = SubscriptionSyncLifecycle()
