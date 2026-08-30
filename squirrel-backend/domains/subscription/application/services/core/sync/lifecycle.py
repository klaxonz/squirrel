from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.sync.run_service import SubscriptionSyncRunService
from domains.subscription.application.services.core.sync.state._ownership import has_live_execution_token
from domains.subscription.application.services.core.sync.state.service import SubscriptionSyncStateService
from domains.subscription.application.services.core.update.command_events import SubscriptionSyncCommandEventPublisher
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
from domains.subscription.application.services.crawl.tasks.errors import CrawlExecutionError, CrawlTaskStateError
from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.subscription.application.services.crawl.tasks.task_types import resolve_subscription_sync_task_type
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.subscription.domain.models.subscription_sync_run import SubscriptionSyncRun, SyncRunStatus
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
        crawl_tasks: CrawlTaskService | None = None,
        event_publisher: SubscriptionSyncCommandEventPublisher | None = None,
        crud_service: SubscriptionCrudService | None = None,
        run_service: SubscriptionSyncRunService | None = None,
    ):
        self.session_factory = session_factory or get_session
        self._sync_state_service = sync_state_service or SubscriptionSyncStateService(
            session_factory=self.session_factory,
        )
        self._crawl_tasks = crawl_tasks or CrawlTaskService(session_factory=self.session_factory)
        self._crud_service = crud_service or SubscriptionCrudService(session_factory=self.session_factory)
        self._run_service = run_service or SubscriptionSyncRunService(self.session_factory)
        self._event_publisher = event_publisher or SubscriptionSyncCommandEventPublisher(self._run_service)
        self._queue_planner = SubscriptionSyncQueuePlanner(self._sync_state_service, self._event_publisher)
        self._orchestrator = None

    def bind_orchestrator(self, orchestrator) -> None:
        self._orchestrator = orchestrator

    def _require_orchestrator(self):
        if self._orchestrator is None:
            raise RuntimeError('SubscriptionSyncLifecycle requires a bound SubscriptionOrchestrator')
        return self._orchestrator

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
        cursor_payload: dict | None = None,
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
            prepare_deferred_state=lambda reason: self._prepare_preflight_deferred_state(command, reason),
        )
        if preflight is not None:
            return preflight

        with self.session_factory() as session:
            queued = self._queue_planner.queue_sync_state_in_session(
                session,
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
                cursor_payload=cursor_payload,
            )
            _, task = self._crawl_tasks.create_job_with_task_in_session(
                session,
                job_type='subscription_sync',
                source_type='manual' if command.trigger == UpdateTrigger.MANUAL else 'scheduled',
                site=domain,
                subscription_id=command.subscription_id,
                priority=resolve_priority(command.trigger, command.mode),
                task_type=resolve_subscription_sync_task_type(command.mode.value),
                payload=task_payload,
                sync_state_id=queued.sync_state_id,
                run_id=queued.run_context.run_id,
                trace_id=command.trace_id,
            )
            request_id = str(task.id)
            task.payload = {**(task.payload or {}), 'request_id': request_id}
            run = session.get(SubscriptionSyncRun, queued.run_context.run_id)
            if run is not None:
                run.request_id = request_id
            session.flush()

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
        cursor_payload: dict | None = None,
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
            prepare_deferred_state=lambda reason: self._prepare_preflight_deferred_state(command, reason),
        )
        if isinstance(preflight, SubscriptionDirectRunResult):
            return preflight

        with self.session_factory() as session:
            queued = self._queue_planner.queue_sync_state_in_session(
                session,
                command,
                domain=domain,
                scheduled=False,
            )
            if queued.status != 'ready':
                return SubscriptionDirectRunResult(
                    subscription_id=command.subscription_id,
                    sync_state_id=queued.sync_state_id,
                    status=queued.status,
                    run_id=queued.run_context.run_id if queued.run_context else command.run_id,
                )
            request_id = f'direct:{queued.run_context.run_id}'
            run = session.get(SubscriptionSyncRun, queued.run_context.run_id)
            if run is not None:
                run.request_id = request_id

        from domains.subscription.application.services.crawl.executors.subscription_sync_executor import (
            CrawlExecutorService,
        )

        try:
            sync_result = CrawlExecutorService(
                lifecycle=self,
                orchestrator_service=self._require_orchestrator(),
                subscription_svc=self._crud_service,
            ).execute_subscription_sync_payload(
                {
                    **build_task_payload(
                        command,
                        queued.sync_state_id,
                        queued.queue_token,
                        request_id=request_id,
                        run_id=queued.run_context.run_id,
                        cursor_payload=cursor_payload,
                    ),
                    'inline_video_extraction': True,
                    'execution_token': request_id,
                },
            )
        except (CrawlExecutionError, ValueError, TypeError, AttributeError, KeyError) as exc:
            self._sync_state_service.mark_sync_failed(
                queued.sync_state_id,
                str(exc),
                error_type=str(getattr(exc, 'error_type', None) or type(exc).__name__),
                run_id=queued.run_context.run_id,
                queue_token=queued.queue_token,
                execution_token=request_id,
            )
            sync_result = SubscriptionUpdateResult(
                subscription_id=command.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(exc),
                error_type=str(getattr(exc, 'error_type', None) or type(exc).__name__),
                retryable=bool(getattr(exc, 'retryable', False)),
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
        execution_token: str | None = None,
        request_id: str | None = None,
        trace_id: str | None = None,
        trigger: str | None = None,
    ):
        return self._sync_state_service.claim_sync_state(
            sync_state_id,
            queue_token,
            run_id=run_id,
            execution_token=execution_token,
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
        with self.session_factory() as session:
            states = session.execute(
                select(SubscriptionSyncState)
                .where(SubscriptionSyncState.subscription_id == subscription_id)
                .order_by(SubscriptionSyncState.id.asc())
                .with_for_update(),
            ).scalars().all()
            subscription = session.execute(
                select(Subscription).where(Subscription.id == subscription_id).with_for_update(),
            ).scalar_one_or_none()
            if subscription is None or not subscription.is_deleted:
                return
            has_active_subscriber = session.execute(
                select(UserSubscription.id)
                .where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                )
                .limit(1),
            ).first() is not None
            if has_active_subscriber:
                return
            self._sync_state_service.deactivate_sync_states_in_session(
                session,
                subscription_id,
                reason=reason,
                states=states,
            )

    def skip_sync(self, request: SubscriptionUpdateRequest, *, reason: str) -> None:
        if not request.sync_state_id:
            return
        self._sync_state_service.mark_sync_skipped(
            request.sync_state_id,
            reason=reason,
            run_id=request.run_id,
            queue_token=request.queue_token,
            execution_token=request.execution_token,
        )

    def fail_sync(self, request: SubscriptionUpdateRequest, error: Exception | str) -> None:
        if not request.sync_state_id:
            return
        self._sync_state_service.mark_sync_failed(
            request.sync_state_id,
            str(error),
            error_type=type(error).__name__ if isinstance(error, Exception) else None,
            run_id=request.run_id,
            queue_token=request.queue_token,
            execution_token=request.execution_token,
        )

    def complete_sync(self, request: SubscriptionUpdateRequest, result: SubscriptionUpdateResult) -> None:
        if not request.sync_state_id:
            return

        if request.mode == UpdateMode.FULL and result.has_more:
            continuation_payload = self._queue_full_continuation(request, result)
            if request.inline_video_extraction:
                self._run_inline_continuation(continuation_payload)
            return

        completion_cursor_payload = {} if request.mode == UpdateMode.FULL else result.cursor_payload
        completed_state = self._sync_state_service.mark_sync_success(
            request.sync_state_id,
            cursor_payload=completion_cursor_payload,
            latest_video_url=result.latest_video_url,
            videos_found=result.videos_found,
            videos_enqueued=result.videos_enqueued,
            run_id=request.run_id,
            queue_token=request.queue_token,
            execution_token=request.execution_token,
            total_available=result.total_available,
        )
        if completed_state is None:
            raise CrawlTaskStateError(
                f'Stale sync completion: sync_state_id={request.sync_state_id}, run_id={request.run_id}',
            )

    def record_gap_observation(
        self,
        request: SubscriptionUpdateRequest,
        result: SubscriptionUpdateResult,
    ) -> None:
        if request.mode != UpdateMode.INCREMENTAL or not request.sync_state_id:
            return

        subscription = self._crud_service.get_subscription_by_id(request.subscription_id)
        local_total = getattr(subscription, 'total_videos', None) if subscription else None
        summary = self._sync_state_service.record_gap_observation(
            sync_state_id=request.sync_state_id,
            head_sample_urls=result.head_sample_urls,
            anchor_found=result.anchor_found,
            cursor_invalid=bool(result.cursor_invalid),
            cursor_loop_detected=bool(result.cursor_loop_detected),
            total_available=result.total_available,
            local_total=local_total,
            run_id=request.run_id,
            execution_token=request.execution_token,
        )
        if not summary['should_request_full']:
            return

        site = str(summary['site'] or '').strip()
        if not self._can_request_full_sync(site):
            return

        try:
            scheduled = self.request_sync(
                subscription_id=request.subscription_id,
                url=request.url,
                trigger=request.trigger,
                mode=UpdateMode.FULL,
                trace_id=request.trace_id,
            )
            if scheduled.status != 'queued':
                return
            self._sync_state_service.mark_full_sync_requested(
                request.sync_state_id,
                run_id=request.run_id,
                execution_token=request.execution_token,
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
        if request.sync_state_id and not self._has_live_request_execution(request):
            raise CrawlTaskStateError(
                f'Stale total-video backfill request: sync_state_id={request.sync_state_id}, run_id={request.run_id}',
            )

        subscription = self._crud_service.get_subscription_by_id(request.subscription_id)
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

        try:
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
        except Exception:
            logger.exception(
                'Failed to schedule total-video backfill: subscription_id=%s',
                request.subscription_id,
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
        execution_token: str | None = None,
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
            execution_token=execution_token,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
        )

    def record_video_extraction_enqueued(
        self,
        sync_state_id: int | None,
        *,
        run_id: str | None = None,
        execution_token: str | None = None,
    ) -> None:
        reserved = self._sync_state_service.increment_pending_video_count(
            sync_state_id,
            1,
            run_id=run_id,
            execution_token=execution_token,
        )
        if sync_state_id and run_id and execution_token and not reserved:
            raise CrawlTaskStateError(
                f'Stale video extraction reservation: sync_state_id={sync_state_id}, run_id={run_id}',
            )

    def record_video_extraction_dispatch_failed(
        self,
        sync_state_id: int | None,
        *,
        run_id: str | None = None,
        execution_token: str | None = None,
    ) -> None:
        self._sync_state_service.decrement_pending_video_count(
            sync_state_id,
            allow_completion=False,
            run_id=run_id,
            execution_token=execution_token,
        )

    def record_video_extraction_terminal(
        self,
        sync_state_id: int | None,
        *,
        succeeded: bool,
        run_id: str | None = None,
        execution_token: str | None = None,
    ) -> None:
        if succeeded:
            self._sync_state_service.decrement_pending_video_count(
                sync_state_id,
                allow_completion=True,
                run_id=run_id,
                execution_token=execution_token,
            )
            return
        self._sync_state_service.decrement_pending_video_count(
            sync_state_id,
            allow_completion=False,
            run_id=run_id,
            execution_token=execution_token,
        )
        if sync_state_id:
            self._sync_state_service.reconcile_terminal_drained_sync_states(sync_state_id)

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

    def _queue_full_continuation(
        self,
        request: SubscriptionUpdateRequest,
        result: SubscriptionUpdateResult,
    ) -> dict:
        if not request.sync_state_id or not request.run_id or not request.queue_token:
            raise CrawlTaskStateError('Full-sync continuation is missing its fencing identity')

        command = build_command(
            subscription_id=request.subscription_id,
            url=request.url,
            trigger=request.trigger,
            mode=request.mode,
            user_id=request.user_id,
            force=request.force,
            trace_id=request.trace_id,
            run_id=request.run_id,
        )
        now = datetime.now()
        next_queue_token = self._sync_state_service.build_queue_token()

        with self.session_factory() as session:
            state = session.execute(
                select(SubscriptionSyncState)
                .where(SubscriptionSyncState.id == request.sync_state_id)
                .with_for_update(),
            ).scalar_one_or_none()
            if (
                state is None
                or state.current_run_id != request.run_id
                or state.queue_token != request.queue_token
                or state.execution_token != request.execution_token
                or state.sync_status != SyncStatus.RUNNING.value
                or not has_live_execution_token(session, state, request.execution_token)
            ):
                raise CrawlTaskStateError(
                    f'Stale full-sync continuation: sync_state_id={request.sync_state_id}, run_id={request.run_id}',
                )

            state.cursor_payload = result.cursor_payload or {}
            if result.latest_video_url and not state.last_seen_video_url:
                state.last_seen_video_url = result.latest_video_url
            state.sync_status = SyncStatus.QUEUED.value
            state.queue_token = next_queue_token
            state.execution_token = None
            state.queued_at = now
            state.locked_at = None
            state.last_sync_at = now
            state.last_error = None
            if result.total_available is not None:
                subscription = session.get(Subscription, request.subscription_id)
                if subscription is not None:
                    subscription.total_videos = max(0, int(result.total_available))
            state.version += 1
            self._run_service.mark_status_in_session(
                session,
                request.run_id,
                SyncRunStatus.QUEUED.value,
                queue_token=next_queue_token,
                cursor_out=result.cursor_payload,
                videos_found=result.videos_found,
                videos_enqueued=result.videos_enqueued,
                now=now,
            )

            task_payload = build_task_payload(
                command,
                request.sync_state_id,
                next_queue_token,
                request_id=None,
                run_id=request.run_id,
                cursor_payload=result.cursor_payload,
            )
            if request.inline_video_extraction:
                return {
                    **task_payload,
                    'request_id': f'direct:{request.run_id}',
                    'execution_token': request.execution_token,
                    'inline_video_extraction': True,
                }

            _, task = self._crawl_tasks.create_job_with_task_in_session(
                session,
                job_type='subscription_sync',
                source_type='manual' if request.trigger == UpdateTrigger.MANUAL else 'scheduled',
                site=resolve_site(request.url),
                subscription_id=request.subscription_id,
                priority=resolve_priority(request.trigger, request.mode),
                task_type=resolve_subscription_sync_task_type(request.mode.value),
                payload=task_payload,
                sync_state_id=request.sync_state_id,
                run_id=request.run_id,
                trace_id=request.trace_id,
            )
            task.payload = {**task_payload, 'request_id': str(task.id)}
            session.flush()
            return task.payload

    def _run_inline_continuation(self, payload: dict) -> None:
        from domains.subscription.application.services.crawl.executors.subscription_sync_executor import (
            CrawlExecutorService,
        )

        CrawlExecutorService(
            lifecycle=self,
            orchestrator_service=self._require_orchestrator(),
            subscription_svc=self._crud_service,
        ).execute_subscription_sync_payload(payload)

    def _can_request_full_sync(self, site: str) -> bool:
        global_limit = max(1, int(settings.FULL_SYNC_MAX_INFLIGHT))
        site_limit = max(1, int(settings.FULL_SYNC_SITE_MAX_INFLIGHT))

        with self.session_factory() as session:
            global_inflight = int(
                session.execute(
                    select(func.count(SubscriptionSyncState.id)).where(
                        SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                        SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
                    ),
                ).scalar_one()
                or 0
            )
            if global_inflight >= global_limit:
                return False

            if site:
                site_inflight = int(
                    session.execute(
                        select(func.count(SubscriptionSyncState.id)).where(
                            SubscriptionSyncState.sync_mode == SyncMode.FULL.value,
                            SubscriptionSyncState.sync_status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value]),
                            SubscriptionSyncState.site == site,
                        ),
                    ).scalar_one()
                    or 0
                )
                if site_inflight >= site_limit:
                    return False

        return True

    def _has_live_request_execution(self, request: SubscriptionUpdateRequest) -> bool:
        if not request.sync_state_id:
            return True
        with self.session_factory() as session:
            state = session.execute(
                select(SubscriptionSyncState)
                .where(SubscriptionSyncState.id == request.sync_state_id)
                .with_for_update(),
            ).scalar_one_or_none()
            return bool(
                state is not None
                and state.current_run_id == request.run_id
                and state.queue_token == request.queue_token
                and has_live_execution_token(session, state, request.execution_token)
            )

    def _prepare_preflight_deferred_state(self, command, reason: str) -> int | None:
        now = datetime.now()
        with self.session_factory() as session:
            state, status = self._sync_state_service.prepare_sync_state_for_enqueue_in_session(
                session,
                command.subscription_id,
                command.url,
                command.mode.value,
                scheduled=False,
                now=now,
            )
            if state is None:
                return None
            if status not in {'queued', 'in_progress'}:
                state.sync_status = SyncStatus.SUCCESS.value
                state.last_sync_at = now
                state.last_error = reason
                state.queue_token = None
                state.current_run_id = None
                state.queued_at = None
                state.locked_at = None
                state.next_sync_at = now + timedelta(hours=6)
                state.version += 1
            return state.id

    def _has_active_subscribers(self, subscription_id: int) -> bool:
        with self.session_factory() as session:
            row = session.execute(
                select(UserSubscription.id)
                .where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                )
                .limit(1),
            ).first()
            return row is not None
