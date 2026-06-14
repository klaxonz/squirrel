from __future__ import annotations

import logging

from sqlalchemy import select

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
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
from domains.subscription.application.services.core.update.queueing import SubscriptionSyncQueuePlanner
from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.application.services.crawl.tasks.task_types import resolve_subscription_sync_task_type
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from infrastructure.database.session import get_session
from infrastructure.site_catalog.url import resolve_site

from .models import (
    SubscriptionDirectRunResult,
    SubscriptionScheduleResult,
    SubscriptionUpdateResult,
    UpdateMode,
    UpdateTrigger,
)

logger = logging.getLogger(__name__)


class SubscriptionSyncCommandService:
    def __init__(self, session_factory=None, sync_state_service=None, crawl_tasks=None, event_publisher: SubscriptionSyncCommandEventPublisher | None = None):
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

        queued = self._queue_planner.queue_sync_state(command, domain=domain, scheduled=command.trigger == UpdateTrigger.SCHEDULED)
        if queued.status != "ready":
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
            job_type="subscription_sync",
            source_type="manual" if command.trigger == UpdateTrigger.MANUAL else "scheduled",
            site=domain,
            subscription_id=command.subscription_id,
            priority=resolve_priority(command.trigger, command.mode),
            task_type=resolve_subscription_sync_task_type(command.mode.value),
            payload=task_payload,
            trace_id=command.trace_id,
        )
        request_id = str(task.id)
        task.payload["request_id"] = request_id
        self._set_task_request_id(task.id, request_id)

        self._event_publisher.append_queued_event(
            command,
            sync_state_id=queued.sync_state_id,
            domain=domain,
            queue_token=queued.queue_token,
            request_id=request_id,
            run_context=queued.run_context,
            pending_video_count=queued.pending_video_count,
        )
        logger.debug(
            "Queued subscription sync task subscription_id=%s sync_state_id=%s task_id=%s priority=%s",
            command.subscription_id,
            queued.sync_state_id,
            task.id,
            resolve_priority(command.trigger, command.mode),
        )
        return SubscriptionScheduleResult(
            subscription_id=command.subscription_id,
            sync_state_id=queued.sync_state_id,
            status="queued",
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
        if queued.status != "ready":
            return SubscriptionDirectRunResult(
                subscription_id=command.subscription_id,
                sync_state_id=queued.sync_state_id,
                status=queued.status,
                run_id=queued.run_context.run_id if queued.run_context else command.run_id,
            )

        request_id = f"direct:{queued.run_context.run_id}"
        self._event_publisher.append_queued_event(
            command,
            sync_state_id=queued.sync_state_id,
            domain=domain,
            queue_token=queued.queue_token,
            request_id=request_id,
            run_context=queued.run_context,
            pending_video_count=queued.pending_video_count,
            direct=True,
        )

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
                "inline_video_extraction": True,
            })
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            self._sync_state_service.mark_sync_failed(
                queued.sync_state_id,
                str(exc),
                run_id=queued.run_context.run_id,
                request_id=request_id,
                trace_id=command.trace_id,
                error_type=type(exc).__name__,
                trigger=command.trigger.value,
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
            status="success" if sync_result.success else "failed",
            request_id=request_id,
            run_id=queued.run_context.run_id,
            result=sync_result,
        )

    def _set_task_request_id(self, task_id: int, request_id: str) -> None:
        from domains.subscription.domain.models.crawl_task import CrawlTask

        with self.session_factory() as session:
            task = session.get(CrawlTask, task_id)
            if task is None:
                return
            task.payload = {**(task.payload or {}), "request_id": request_id}

    def _has_active_subscribers(self, subscription_id: int) -> bool:
        with self.session_factory() as session:
            row = session.execute(
                select(UserSubscription.id).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ).limit(1),
            ).first()
            return row is not None

subscription_sync_command_service = SubscriptionSyncCommandService()
request_sync = subscription_sync_command_service.request_sync
run_inline_sync = subscription_sync_command_service.run_inline_sync
