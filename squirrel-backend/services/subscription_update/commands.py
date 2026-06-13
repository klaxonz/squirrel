from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from services import subscription_sync_state_service
from services.crawl_tasks import service as crawl_task_service
from services.crawl_tasks.task_types import resolve_subscription_sync_task_type
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncPhase, SyncRunContext, SyncRunStatus, create_run
from utils.site_catalog import SiteCatalog
from utils.trace import generate_trace_id, get_trace_id
from utils.url_helper import resolve_site

from .models import (
    SubscriptionDirectRunResult,
    SubscriptionScheduleResult,
    SubscriptionUpdateResult,
    UpdateMode,
    UpdateTrigger,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncCommand:
    subscription_id: int
    url: str
    trigger: UpdateTrigger
    mode: UpdateMode
    user_id: int | None = None
    force: bool = False
    trace_id: str | None = None
    run_id: str | None = None


class SubscriptionSyncCommandService:
    def __init__(self, session_factory=None, sync_state_service=None, crawl_tasks=None):
        self.session_factory = session_factory or get_session
        self._sync_state_service = sync_state_service or subscription_sync_state_service
        self._crawl_tasks = crawl_tasks or crawl_task_service

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
        command = self._build_command(
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
        preflight = self._preflight(command, domain)
        if preflight is not None:
            return preflight

        queued = self._queue_sync_state(command, domain=domain, scheduled=command.trigger == UpdateTrigger.SCHEDULED)
        if queued.status != "ready":
            return SubscriptionScheduleResult(
                subscription_id=command.subscription_id,
                sync_state_id=queued.sync_state_id,
                status=queued.status,
                run_id=queued.run_context.run_id if queued.run_context else command.run_id,
            )

        task_payload = self._build_task_payload(
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
            priority=self._resolve_priority(command.trigger, command.mode),
            task_type=resolve_subscription_sync_task_type(command.mode.value),
            payload=task_payload,
            trace_id=command.trace_id,
        )
        request_id = str(task.id)
        task.payload["request_id"] = request_id
        self._set_task_request_id(task.id, request_id)

        self._append_queued_event(
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
            self._resolve_priority(command.trigger, command.mode),
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
        command = self._build_command(
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
        preflight = self._preflight(command, domain, direct=True)
        if isinstance(preflight, SubscriptionDirectRunResult):
            return preflight

        queued = self._queue_sync_state(command, domain=domain, scheduled=False)
        if queued.status != "ready":
            return SubscriptionDirectRunResult(
                subscription_id=command.subscription_id,
                sync_state_id=queued.sync_state_id,
                status=queued.status,
                run_id=queued.run_context.run_id if queued.run_context else command.run_id,
            )

        request_id = f"direct:{queued.run_context.run_id}"
        self._append_queued_event(
            command,
            sync_state_id=queued.sync_state_id,
            domain=domain,
            queue_token=queued.queue_token,
            request_id=request_id,
            run_context=queued.run_context,
            pending_video_count=queued.pending_video_count,
            direct=True,
        )

        from services.crawl_executors.subscription_sync_executor import execute_subscription_sync_payload

        try:
            sync_result = execute_subscription_sync_payload({
                **self._build_task_payload(
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

    def _build_command(self, **kwargs) -> SyncCommand:
        mode = kwargs["mode"]
        resolved_mode = UpdateMode.FULL if mode == UpdateMode.FULL else UpdateMode.INCREMENTAL
        return SyncCommand(
            **{
                **kwargs,
                "mode": resolved_mode,
                "trace_id": kwargs.get("trace_id") or get_trace_id() or generate_trace_id(),
            },
        )

    def _preflight(
        self,
        command: SyncCommand,
        domain: str | None,
        *,
        direct: bool = False,
    ) -> SubscriptionScheduleResult | SubscriptionDirectRunResult | None:
        if not domain or not SiteCatalog.is_site_enabled(domain=domain):
            run_context = self._emit_deferred_event(command, None, domain, "site_disabled")
            if direct:
                return SubscriptionDirectRunResult(
                    command.subscription_id,
                    None,
                    "site_disabled",
                    run_id=run_context.run_id,
                    result=SubscriptionUpdateResult(
                        subscription_id=command.subscription_id,
                        success=True,
                        videos_found=0,
                        videos_enqueued=0,
                        skipped_reason="site_disabled",
                    ),
                )
            return SubscriptionScheduleResult(command.subscription_id, None, "site_disabled", run_id=run_context.run_id)

        if not self._has_active_subscribers(command.subscription_id):
            run_context = self._emit_deferred_event(command, None, domain, "no_subscribers")
            if direct:
                return SubscriptionDirectRunResult(
                    command.subscription_id,
                    None,
                    "no_subscribers",
                    run_id=run_context.run_id,
                    result=SubscriptionUpdateResult(
                        subscription_id=command.subscription_id,
                        success=True,
                        videos_found=0,
                        videos_enqueued=0,
                        skipped_reason="no_subscribers",
                    ),
                )
            return SubscriptionScheduleResult(command.subscription_id, None, "no_subscribers", run_id=run_context.run_id)
        return None

    def _queue_sync_state(self, command: SyncCommand, *, domain: str, scheduled: bool):
        state, state_status = self._sync_state_service.prepare_sync_state_for_enqueue(
            command.subscription_id,
            command.url,
            command.mode.value,
            scheduled=scheduled,
        )
        if not state:
            return _QueuedSync(None, "failed", None, None, 0)

        run_context, emit_run_created = self._build_run_context(
            subscription_id=command.subscription_id,
            sync_state_id=state.id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            run_id=command.run_id,
        )
        if emit_run_created:
            self._append_run_created(command, state.id, domain, run_context, state.pending_video_count)

        if state_status == "deferred":
            self._append_deferred_event(command, state.id, domain, run_context, "queue_backpressure", state.pending_video_count)
            return _QueuedSync(state.id, "deferred", run_context, None, state.pending_video_count)
        if state_status in {"in_progress", "queued"}:
            return _QueuedSync(state.id, state_status, run_context, None, state.pending_video_count)

        queue_token = self._sync_state_service.build_queue_token()
        queued_state = self._sync_state_service.queue_sync_state(state.id, queue_token)
        if not queued_state:
            return _QueuedSync(state.id, "failed", run_context, None, state.pending_video_count)
        if queued_state.queue_token != queue_token:
            status = "in_progress" if queued_state.sync_status == "running" else "queued"
            self._append_deferred_event(command, queued_state.id, domain, run_context, "queue_state_mismatch", queued_state.pending_video_count)
            return _QueuedSync(queued_state.id, status, run_context, None, queued_state.pending_video_count)
        if queued_state.sync_status != "queued":
            self._append_deferred_event(command, queued_state.id, domain, run_context, "queue_state_invalid", queued_state.pending_video_count)
            return _QueuedSync(queued_state.id, "failed", run_context, None, queued_state.pending_video_count)
        return _QueuedSync(queued_state.id, "ready", run_context, queue_token, queued_state.pending_video_count)

    def _build_task_payload(
        self,
        command: SyncCommand,
        sync_state_id: int,
        queue_token: str,
        *,
        request_id: str | None,
        run_id: str,
    ) -> dict:
        return {
            "subscription_id": command.subscription_id,
            "url": command.url,
            "sync_state_id": sync_state_id,
            "mode": command.mode.value,
            "user_id": command.user_id,
            "force": command.force,
            "queue_token": queue_token,
            "trigger": command.trigger.value,
            "run_id": run_id,
            "trace_id": command.trace_id,
            "request_id": request_id,
        }

    def _set_task_request_id(self, task_id: int, request_id: str) -> None:
        from models.crawl_task import CrawlTask

        with self.session_factory() as session:
            task = session.get(CrawlTask, task_id)
            if task is None:
                return
            task.payload = {**(task.payload or {}), "request_id": request_id}

    @staticmethod
    def _resolve_priority(trigger: UpdateTrigger, mode: UpdateMode) -> str:
        if trigger == UpdateTrigger.MANUAL:
            return "manual"
        if mode == UpdateMode.FULL:
            return "full"
        return "incr"

    def _has_active_subscribers(self, subscription_id: int) -> bool:
        with self.session_factory() as session:
            row = session.execute(
                select(UserSubscription.id).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                ).limit(1),
            ).first()
            return row is not None

    @staticmethod
    def _build_run_context(
        *,
        subscription_id: int,
        sync_state_id: int | None,
        site: str | None,
        sync_mode: str,
        trigger: str,
        trace_id: str,
        run_id: str | None,
    ) -> tuple[SyncRunContext, bool]:
        if run_id:
            now = datetime.now()
            return (
                SyncRunContext(
                    run_id=run_id,
                    stream_id=run_id,
                    subscription_id=subscription_id,
                    sync_state_id=sync_state_id,
                    site=(site or "").strip(),
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

    def _emit_deferred_event(self, command: SyncCommand, sync_state_id: int | None, domain: str | None, reason: str) -> SyncRunContext:
        run_context, emit_run_created = self._build_run_context(
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            run_id=command.run_id,
        )
        if emit_run_created:
            self._append_run_created(command, sync_state_id, domain, run_context, 0)
        self._append_deferred_event(command, sync_state_id, domain, run_context, reason, 0)
        return run_context

    @staticmethod
    def _append_run_created(
        command: SyncCommand,
        sync_state_id: int | None,
        domain: str | None,
        run_context: SyncRunContext,
        pending_video_count: int,
    ) -> None:
        append_event(SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            event_type=SyncEventType.RUN_CREATED,
            event_phase=SyncPhase.INIT,
            event_status=SyncRunStatus.CREATED,
            payload={"pending_video_count": pending_video_count},
            occurred_at=run_context.created_at,
        ))

    @staticmethod
    def _append_queued_event(
        command: SyncCommand,
        *,
        sync_state_id: int,
        domain: str,
        queue_token: str,
        request_id: str,
        run_context: SyncRunContext,
        pending_video_count: int,
        direct: bool = False,
    ) -> None:
        payload = {
            "queue_token": queue_token,
            "pending_video_count": pending_video_count,
        }
        if direct:
            payload["direct"] = True
        append_event(SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            request_id=request_id,
            trace_id=command.trace_id,
            event_type=SyncEventType.QUEUED,
            event_phase=SyncPhase.QUEUED,
            event_status=SyncRunStatus.QUEUED,
            payload=payload,
        ))

    @staticmethod
    def _append_deferred_event(
        command: SyncCommand,
        sync_state_id: int | None,
        domain: str | None,
        run_context: SyncRunContext,
        reason: str,
        pending_video_count: int,
    ) -> None:
        append_event(SyncEventInput(
            stream_id=run_context.run_id,
            subscription_id=command.subscription_id,
            sync_state_id=sync_state_id,
            site=domain,
            sync_mode=command.mode.value,
            trigger=command.trigger.value,
            trace_id=command.trace_id,
            event_type=SyncEventType.DEFERRED,
            event_phase=SyncPhase.DEFERRED,
            event_status=SyncRunStatus.DEFERRED,
            payload={
                "reason": reason,
                "pending_video_count": pending_video_count,
                "error_message": reason,
            },
        ))


@dataclass(frozen=True)
class _QueuedSync:
    sync_state_id: int | None
    status: str
    run_context: SyncRunContext | None
    queue_token: str | None
    pending_video_count: int


_default = SubscriptionSyncCommandService()
request_sync = _default.request_sync
run_inline_sync = _default.run_inline_sync
