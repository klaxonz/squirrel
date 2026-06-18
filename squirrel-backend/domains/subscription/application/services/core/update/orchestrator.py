"""Subscription update orchestrator
Unified entry point responsible for coordinating the entire update flow
"""
from __future__ import annotations

import logging

from sqlalchemy import select

import domains.subscription.application.services.core.sync.state.service as subscription_sync_state_service
import infrastructure.site_catalog.url as url_helper
from domains.subscription.application.services.core.crud import get_subscription_by_id
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription_sync_state import SyncMode
from infrastructure.database.session import get_session
from infrastructure.site_catalog.catalog import SiteCatalog

from .models import SubscriptionUpdateRequest, SubscriptionUpdateResult, UpdateMode, UpdateTrigger
from .strategies.default_strategy import DefaultUpdateStrategy, should_schedule_total_video_backfill

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
                        reason="site_disabled",
                    )
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
                        reason="no_subscribers",
                    )
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=True,
                    videos_found=0,
                    videos_enqueued=0,
                    skipped_reason="no_subscribers",
                )

            logger.debug(
                "Updating subscription %s (trigger=%s, mode=%s)",
                request.subscription_id,
                request.trigger.value,
                request.mode.value,
            )

            result = self.default_strategy.execute(request)
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
                    error_type=type(e).__name__,
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
                videos_found=result.videos_found,
            )
            self._schedule_continuation(request)
            return

        subscription_sync_state_service.mark_sync_success(
            request.sync_state_id,
            cursor_payload=result.cursor_payload,
            latest_video_url=result.latest_video_url,
            videos_found=result.videos_found,
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


orchestrator = SubscriptionOrchestrator()

