"""Subscription update orchestrator
Unified entry point responsible for coordinating the entire update flow
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

import services.subscription.sync.state.service as subscription_sync_state_service
from core.database import get_session
from models.links import UserSubscription
from models.subscription_sync_state import SyncMode
from services.observability.collector.instance import metrics
from services.site_catalog.catalog import SiteCatalog
from services.subscription.crud import get_subscription_by_id
from utils import url_helper

from .models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateMode, UpdateTrigger
from .strategies.default_strategy import DefaultUpdateStrategy, should_schedule_total_video_backfill
from .strategies.registry import StrategyRegistry

if TYPE_CHECKING:
    from services.subscription.update.strategies.base import UpdateStrategy

logger = logging.getLogger(__name__)


class SubscriptionOrchestrator:
    """Subscription update orchestrator

    Responsibilities:
    1. Receive update requests
    2. Select appropriate update strategy
    3. Execute update flow
    4. Return update results
    """

    def __init__(self, session_factory=None):
        self.default_strategy = DefaultUpdateStrategy()
        self.session_factory = session_factory or get_session

    def update(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """Execute subscription update

        Args:
            request: Update request

        Returns:
            Update result

        """
        try:
            domain = url_helper.extract_top_level_domain(request.url)
            if not SiteCatalog.is_site_enabled(domain=domain):
                message = f"Site is disabled, skip subscription update: {domain}"
                logger.info(message)
                if request.sync_state_id:
                    subscription_sync_state_service.mark_sync_skipped(
                        request.sync_state_id,
                        run_id=request.run_id,
                        request_id=request.request_id,
                        trace_id=request.trace_id,
                        trigger=request.trigger.value,
                        reason="site_disabled",
                    )
                # 记录跳过指标
                metrics.counter("subscription.update.total", tags={"site": domain, "status": "skipped", "reason": "site_disabled"})
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=True,
                    videos_found=0,
                    videos_enqueued=0,
                    skipped_reason="site_disabled",
                )

            if not self._has_active_subscribers(request.subscription_id):
                message = f"No active subscribers, skip subscription update: subscription_id={request.subscription_id}"
                logger.info(message)
                if request.sync_state_id:
                    subscription_sync_state_service.mark_sync_skipped(
                        request.sync_state_id,
                        run_id=request.run_id,
                        request_id=request.request_id,
                        trace_id=request.trace_id,
                        trigger=request.trigger.value,
                        reason="no_subscribers",
                    )
                metrics.counter("subscription.update.total", tags={"site": domain, "status": "skipped", "reason": "no_subscribers"})
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=True,
                    videos_found=0,
                    videos_enqueued=0,
                    skipped_reason="no_subscribers",
                )

            site_name = self._resolve_site(request.url)
            strategy = self._select_strategy(site_name)

            logger.debug(
                "Updating subscription %s using %s strategy (trigger=%s, mode=%s)",
                request.subscription_id,
                strategy.site_name,
                request.trigger.value,
                request.mode.value,
            )

            result = strategy.execute(request)
            if result.skipped_reason:
                self._mark_skipped(request, result.skipped_reason)
            elif result.success:
                self._finalize_success(request, result)
                self._record_gap_observation(request, result)
                self._schedule_total_video_backfill(request, result)

            return result

        except Exception as e:  # orchestrator boundary — always return SubscriptionUpdateResult
            logger.error("Orchestrator error for subscription %s: %s", request.subscription_id, e, exc_info=True)
            if request.sync_state_id:
                subscription_sync_state_service.mark_sync_failed(
                    request.sync_state_id,
                    str(e),
                    run_id=request.run_id,
                    request_id=request.request_id,
                    trace_id=request.trace_id,
                    error_type=type(e).__name__,
                    trigger=request.trigger.value,
                )

            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(e),
            )

    @staticmethod
    def _mark_skipped(request: SubscriptionUpdateRequest, reason: str) -> None:
        if not request.sync_state_id:
            return
        subscription_sync_state_service.mark_sync_skipped(
            request.sync_state_id,
            run_id=request.run_id,
            request_id=request.request_id,
            trace_id=request.trace_id,
            trigger=request.trigger.value,
            reason=reason,
        )

    def _finalize_success(self, request: SubscriptionUpdateRequest, result: SubscriptionUpdateResult) -> None:
        if not request.sync_state_id:
            return

        if request.mode == UpdateMode.FULL and result.has_more:
            subscription_sync_state_service.continue_full_sync_batch(
                request.sync_state_id,
                cursor_payload=result.cursor_payload,
                latest_video_url=result.latest_video_url,
                source_video_count=result.source_video_count,
                videos_found=result.videos_found,
                videos_enqueued=result.videos_enqueued,
                run_id=request.run_id,
                request_id=request.request_id,
                trace_id=request.trace_id,
                trigger=request.trigger.value,
            )
            self._schedule_continuation(request)
            return

        subscription_sync_state_service.mark_sync_success(
            request.sync_state_id,
            cursor_payload=result.cursor_payload,
            latest_video_url=result.latest_video_url,
            source_video_count=result.source_video_count,
            videos_found=result.videos_found,
            videos_enqueued=result.videos_enqueued,
            run_id=request.run_id,
            request_id=request.request_id,
            trace_id=request.trace_id,
            trigger=request.trigger.value,
        )

    @staticmethod
    def _schedule_continuation(request: SubscriptionUpdateRequest) -> None:
        from .scheduler import scheduler

        if request.inline_video_extraction:
            continuation_result = scheduler.run_one_inline(
                subscription_id=request.subscription_id,
                url=request.url,
                trigger=request.trigger,
                mode=request.mode,
                user_id=request.user_id,
                force=request.force,
                trace_id=request.trace_id,
                run_id=request.run_id,
            )
            expected_status = "success"
        else:
            continuation_result = scheduler.schedule_one(
                subscription_id=request.subscription_id,
                url=request.url,
                trigger=request.trigger,
                mode=request.mode,
                user_id=request.user_id,
                force=request.force,
                trace_id=request.trace_id,
                run_id=request.run_id,
            )
            expected_status = "queued"

        if continuation_result.status != expected_status:
            raise ValueError(
                f"Failed to continue subscription sync: subscription_id={request.subscription_id}, "
                f"status={continuation_result.status}",
            )

    @staticmethod
    def _record_gap_observation(request: SubscriptionUpdateRequest, result: SubscriptionUpdateResult) -> None:
        if request.mode != UpdateMode.INCREMENTAL or not request.sync_state_id:
            return

        subscription = get_subscription_by_id(request.subscription_id)
        local_total = getattr(subscription, "total_videos", None) if subscription else None
        subscription_sync_state_service.record_gap_observation(
            sync_state_id=request.sync_state_id,
            head_sample_urls=result.head_sample_urls,
            anchor_found=result.anchor_found,
            cursor_invalid=bool(result.cursor_invalid),
            cursor_loop_detected=bool(result.cursor_loop_detected),
            total_available=result.total_available,
            local_total=local_total,
            trigger=request.trigger.value,
            trace_id=request.trace_id,
        )

    @staticmethod
    def _schedule_total_video_backfill(
        request: SubscriptionUpdateRequest,
        result: SubscriptionUpdateResult,
    ) -> None:
        if request.inline_video_extraction:
            return

        subscription = get_subscription_by_id(request.subscription_id)
        if not subscription:
            return

        full_state = subscription_sync_state_service.get_sync_state(request.subscription_id, SyncMode.FULL.value)
        if not should_schedule_total_video_backfill(
            request.mode.value,
            subscription.total_videos,
            result.total_available,
            full_state.sync_status if full_state else None,
            full_state.last_success_at if full_state else None,
        ):
            return

        from .scheduler import scheduler

        scheduled = scheduler.schedule_one(
            subscription_id=request.subscription_id,
            url=request.url,
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.FULL,
            trace_id=request.trace_id,
        )
        logger.info(
            "Scheduled full sync to backfill total videos: subscription_id=%s, status=%s",
            request.subscription_id,
            scheduled.status,
        )

    def _has_active_subscribers(self, subscription_id: int) -> bool:
        with self.session_factory() as session:
            row = session.execute(
                select(UserSubscription.id).where(
                    UserSubscription.subscription_id == subscription_id,
                    UserSubscription.is_deleted.is_(False),
                )
                .limit(1),
            ).first()
            return row is not None

    def _resolve_site(self, url: str) -> str:
        """Resolve site name"""
        domain = url_helper.extract_top_level_domain(url)

        site_key, _ = SiteCatalog.find_site_by_domain(domain)
        if site_key:
            return site_key

        return "default"

    def _select_strategy(self, site_name: str) -> UpdateStrategy:
        """Select update strategy"""
        strategy = StrategyRegistry.get_strategy(site_name)
        if strategy:
            logger.debug("Using %s strategy", site_name)
            return strategy

        logger.debug("No specific strategy for %s, using default", site_name)
        return self.default_strategy


orchestrator = SubscriptionOrchestrator()

